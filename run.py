import os
import sys
import copy
import csv
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from configparser import ConfigParser



def parse_period(period_str):

	temp = ''
	years = 0
	months = 0
	between_numbers = True

	for element in period_str:

		if element in {'y', 'm'} :
			if temp.isnumeric():
				if element == 'y':
					years = int(temp)
				else:
					months = int(temp)
				temp = ''
				between_numbers = True
				continue
			else:
				print(f"Invalid number: {temp}")
				exit()


		if between_numbers and element == ' ':
			continue

		between_numbers = False
		temp += element

	return years, months

class Period: 
	def __init__(self, start=None, end=None, weeks=None):
		
		self.start = start
		self.end = end

		if weeks:
			self.end = self.start + relativedelta(weeks=weeks)

	def __str__(self):
		return f"[{self.start} - {self.end}]"


	def inside(self, date):
		return date >= self.start and date <= self.end

	def is_overlap(self, other):
		return other.end >= self.start and other.start <= self.end


	def get_overlap(self, other):

		overlap = Period()

		if self.is_overlap(other):

			if other.start > self.start:
				overlap.start = other.start
			else:
				overlap.start = self.start

			if other.end < self.end:
				overlap.end = other.end
			else:
				overlap.end = self.end

		return overlap

	def days(self):

		return (self.end - self.start).days



def get_next_first_of_month(given_date):
	
	if given_date.day == 1:
		return given_date

	return (given_date + relativedelta(months=1)).replace(day=1)

def get_next_school_year_start(given_date):
	curr_date = given_date.replace(day=1)
	
	while curr_date.month != 9:
		curr_date += relativedelta(months=1)

	return curr_date

write_detailed_month = True
detailed_month = datetime(day=1, month=1, year=2022).date()


class Config:
	format_str = '%d/%m/%Y'
	event_types = ["income", "expense"]
	person_types = ["dad", "mom", "child"]
	# start_date = datetime.strptime("01/08/2021", format_str).date()
	# start_date = get_next_first_of_month(date.today())
	# end_date = datetime(day=1, month=8, year=2050).date() # when I'm 67
	# end_date = datetime(day=1, month=7, year=2021).date() 

	@staticmethod
	def read_file():
		parser = ConfigParser()
		parser.read(Config.proj_dir + '/input_files/config.ini')

		ini_start_date = parser.get('dates','start_date')
		if ini_start_date == 'today':
			Config.start_date = get_next_first_of_month(date.today())
		else:
			Config.start_date = datetime.strptime(ini_start_date, Config.format_str).date()

		ini_end_date = parser.get('dates','end_date')
		Config.end_date = datetime.strptime(ini_end_date, Config.format_str).date()

		Config.project_period = Period(start=Config.start_date, end=Config.end_date)

		Config.initial_saving = parser.getint('money','initail_saving')


class RowFiller:
	
	def __init__(self):
		self.prev_data = dict()
		self.default_data = dict()

	def update(self, row):

		if not self.prev_data:
			self.prev_data = copy.deepcopy(row)
		else:
			for key in self.prev_data.keys():
				if row[key] == "":
					row[key] = self.prev_data[key]
				else:
					self.prev_data[key] = row[key]

		for key in self.default_data.keys():
			if row[key] == "":
				row[key] = self.default_data[key]


#globals
months = dict() # date object / month object
persons = list()
# categories = {"income": set(), "expense": set()}
categories = {}
for event_type in Config.event_types:
	categories[event_type] = set()



def round_by_factor(num, factor):
	return (num//factor)*factor

class Person:
	def __init__(self, row):
		self.name = row['NAME']
		self.type = row['TYPE']
		self.birthday_actual_date = datetime.strptime(row['BIRTHDAY'], Config.format_str).date()
		self.birthday_billing_date = get_next_first_of_month(self.birthday_actual_date)

	def __lt__(self, other):
		""" less than method """
		""" must be defined for sorting """
		return self.birthday_actual_date < other.birthday_actual_date

	def validate(self):
		if self.type not in Config.person_types:
			print("Type is not in ",Config.person_types)
			return False
		if self.name == "":
			print ("Name is empty")
			return False
		return True

	def __repr__(self):
		return f"{self.name}, {self.birthday_actual_date}, {self.birthday_billing_date}"

class MonthEvent:
	def __init__(self, date_event):
		self.type     = date_event.type
		self.category = date_event.category
		self.name     = date_event.name
		self.sum      = date_event.sum
		self.person_type = date_event.person_type

	@staticmethod
	def generate_header_row():
		return ["TYPE","CATEGORY","NAME","SUM"]

	def generate_row(self):
		return [self.type, self.category, self.name, self.sum]



class Month:
	def __init__(self):
		self.month_events = []
		self.agg_categories = dict() # categ. name / aggrate sum
		self.agg_sums = {}
		for event_type in Config.event_types:
			self.agg_sums[event_type] = 0

	def add(self, date_event):
		#update month
		self.month_events.append(MonthEvent(date_event))
		self.agg_sums[date_event.type] += date_event.sum

		if date_event.category in self.agg_categories:
			self.agg_categories[date_event.category] += date_event.sum
		else:
			self.agg_categories[date_event.category] = date_event.sum

	def get_mom_salary(self):
		
		mom_salary = 0

		for i in range(len(self.month_events)):
			if self.month_events[i].category == "salary" and self.month_events[i].person_type == "mom":
				mom_salary =  self.month_events[i].sum
				break
		
		return mom_salary

	def update_mom_salary(self, salary_percentage):

		for i in range(len(self.month_events)):
			if self.month_events[i].category == "salary" and self.month_events[i].person_type == "mom":

				curr_salary = self.month_events[i].sum

				new_salary = salary_percentage*curr_salary
				new_salary = round_by_factor(new_salary, 500)

				self.month_events[i].sum      = new_salary
				self.agg_sums["income"]       = self.agg_sums["income"]       - curr_salary + new_salary
				self.agg_categories["salary"] = self.agg_categories["salary"] - curr_salary + new_salary

				break



class DateEvent:

	def __init__ (self, event_type="", category="", name="", event_sum=0, start=None, end=None, period=1, person_type=""):
		self.type = event_type
		self.category = category
		self.name = name
		self.sum = event_sum
		self.start = start
		self.end = end
		self.period = period
		self.person_type = person_type

	def init_by_row(self, row):
		self.type = row['TYPE']
		self.category = row['CATEGORY']
		self.name = row['NAME']
		self.sum = int(row['SUM'])

		if row['START'] == "today":
			self.start = Config.start_date
		else:
			self.start = datetime.strptime(row['START'], Config.format_str).date()

		if row['END'] == "never":
			self.end = Config.end_date
		else:
			self.end = datetime.strptime(row['END'], Config.format_str).date()
			self.end = min(self.end, Config.end_date)

		y,m = parse_period(row['PERIOD'])
		self.period = y*12 + m

	def init_by_age_event(self, age_event, person):
		self.type = age_event.type
		self.category = age_event.category
		self.name = person.name + ": " + age_event.name
		self.sum = age_event.sum
		
		self.start = person.birthday_billing_date
		while self.start.month != age_event.month_start:
			self.start += relativedelta(months=1)
		self.start += relativedelta(years=age_event.from_age)

		self.end = person.birthday_billing_date + relativedelta(years=age_event.until_age, months=-1)

		self.period = age_event.period
		self.person_type = person.type

	def validate(self):
		if self.type not in Config.event_types:
			print("Type is not in ",Config.event_types)
			return False
		if self.name == "":
			print ("Name is empty")
			return False
		if self.sum < 0:
			print ("Sum is negative")
			return False
		# if self.end < self.start:
		# 	print ("End date is smaller than Start date")
		# 	print (f"start: {self.start}")
		# 	print (f"end: {self.end}")
		# 	return False
		# if self.period < 1:
		# 	print ("Period is less than 1")
		# 	return False
		return True


	def split(self):

		global months
		global categories
		
		if self.end < Config.start_date or self.start > Config.end_date:
			return

		categories[self.type].add(self.category)

		curr_date = self.start

		while curr_date <= self.end:

			if Config.project_period.inside(curr_date):
			
				if months.get(curr_date) is None:
					months[curr_date] = Month()
				
				months[curr_date].add(self)

			curr_date = curr_date + relativedelta(months=self.period) #loop ++

	def __repr__(self):
		return f"{self.name}, {self.sum}, {self.start}, {self.end}"

	def __lt__(self, other):
		""" less than method """
		""" must be defined for sorting """
		return self.start < other.start


def load_date_events(csv_file_name):
	""" Load items from csv and populate months """
	row_filler = RowFiller()
	row_filler.default_data['PERIOD']  = '1m'
	row_filler.default_data['IGNORE']  = 'no'
	row_filler.prev_data['TYPE']     = ''
	row_filler.prev_data['CATEGORY'] = ''
	row_filler.prev_data['NAME']     = ''

	with open(csv_file_name) as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			if row['IGNORE'] == 'yes':
				continue
			row_filler.update(row)
			date_event = DateEvent()
			date_event.init_by_row(row)
			
			if date_event.validate():
				date_event.split()
			else:
				print (date_event.name)
				print("Invalid event data")
				exit()




class AgeEvent:
	BIRTHDAY_MONTH = 0
	def __init__(self, row, person):
		self.type = row['TYPE']
		self.category = row['CATEGORY']
		self.name = row['NAME']
		self.sum = int(row['SUM'])
		self.from_age = int(row['FROM'])
		self.until_age = int(row['UNTIL'])

		y,m = parse_period(row['PERIOD'])
		self.period = y*12 + m

		self.month_start = int(row['MONTH_START'])
		if self.month_start == self.BIRTHDAY_MONTH:
			self.month_start = person.birthday_billing_date.month


def load_persons(csv_file_name):
	
	global persons

	with open(csv_file_name) as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			if row['IGNORE'] == 'yes':
				continue
			persons.append(Person(row))

	for person in persons:
		build_person_payout(person)



def build_person_payout(person):
	
	row_filler = RowFiller()
	row_filler.default_data['PERIOD']      = '1m'
	row_filler.default_data['MONTH_START'] = '0'
	row_filler.default_data['IGNORE']      = 'no'
	row_filler.prev_data['TYPE']     = ''
	row_filler.prev_data['CATEGORY'] = ''
	row_filler.prev_data['NAME']     = ''

	with open(Config.proj_dir + "/input_files/" + person.type+".csv") as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			if row['IGNORE'] == 'yes':
				continue
			row_filler.update(row)
			age_event = AgeEvent(row, person)
			date_event = DateEvent()
			date_event.init_by_age_event(age_event, person)
			date_event.split()

def load_mortgage(csv_file_name):
	
	mortgage_date = Config.start_date

	with open(csv_file_name) as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			pay_sum = float(row['SUM'])
			date_event = DateEvent(event_type="expense", category="דיור", name="משכנתא", event_sum=pay_sum, start=mortgage_date, end=mortgage_date)
			date_event.split()
			mortgage_date += relativedelta(months=1) #loop++

"""

# Calc total child cost

def build_child_payout(person):
	
	row_filler = RowFiller()
	row_filler.default_data['PERIOD']      = '1'
	row_filler.default_data['MONTH_START'] = '0'
	row_filler.default_data['IGNORE']      = 'no'
	row_filler.prev_data['TYPE']     = ''
	row_filler.prev_data['CATEGORY'] = ''
	row_filler.prev_data['NAME']     = ''

	with open(Config.proj_dir + "/input_files/child.csv") as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			if row['IGNORE'] == 'yes':
				continue
			row_filler.update(row)
			age_event = AgeEvent(row, person)


def calc_child():

	from_age = 0
	until_age = 18
	birthday_month = 3 # for tax points and childcare costs
	mom_salary = 11000
	child_order = 1


	incomes = 0
	expenses = 0



	#calc child costs from file - easy

	# calc auto generated events

	# childcare

	# tax points

	curr_age = from_age

	while curr_age != until_age:




	# maternity
	WEEKS_AT_HOME = 26
	WEEKS_BIRTH_SALARY = 15

	if from_age == 0:
		expenses += (WEEKS_AT_HOME-WEEKS_BIRTH_SALARY)*MOM_SALARY
		incomes +=  get_maternity_grant(child_order)

	incomes += (until_age-from_age)*12*get_child_allowance(child_order)

"""





def get_child_allowance(child_order):
	
	CHILD_SAVING = 50
	allowance = 0

	if child_order == 1 or child_order >= 5:
		allowance = 152
	else:
		allowance = 192

	return allowance - CHILD_SAVING

def get_maternity_grant(child_order):
	if child_order == 1:
		return 1783
	elif child_order == 2:
		return 802
	else:
		return 535

def update_incomces_after_births():

	global months

	children = [person for person in persons if person.type == "child"]

	WEEKS_AT_HOME = 26
	WEEKS_BIRTH_SALARY = 15

	child_order = 0

	for child in sorted(children):

		child_order += 1


		### update mom salary from work to zero or partial durring maternity leave

		# update first month salary
		start_date = child.birthday_actual_date
		__, days_in_month = monthrange(start_date.year, start_date.month)
		fraction = start_date.day / days_in_month
		start_pay_date = child.birthday_billing_date
		if months.get(start_pay_date):
			months[start_pay_date].update_mom_salary(fraction)
		
		# update last month salary
		end_date = start_date + relativedelta(weeks=WEEKS_AT_HOME)
		__, days_in_month = monthrange(end_date.year, end_date.month)
		fraction = (days_in_month-end_date.day)/days_in_month
		end_pay_date = get_next_first_of_month(end_date)
		if months.get(end_pay_date):
			months[end_pay_date].update_mom_salary(fraction)

		curr_pay_date = start_pay_date + relativedelta(months=1)
		while curr_pay_date < end_pay_date:
			if months.get(curr_pay_date):
				months[curr_pay_date].update_mom_salary(0)
			curr_pay_date = curr_pay_date + relativedelta(months=1) #loop ++



		### update maternity pay from bituh-leumi

		# claculate last 3 and 6 months avg salary
		sum_salary = 0
		sum_days = 0
		avg_day_salary_3_month = 0
		avg_day_salary_6_month = 0
		curr_pay_date = child.birthday_billing_date - relativedelta(months=1)
		for i in range(6):
			if months.get(curr_pay_date) is not None:
				sum_salary = sum_salary + 1.2*months[curr_pay_date].get_mom_salary() # 1.2 to simulate bruto salary
			__, days_in_month = monthrange(curr_pay_date.year, curr_pay_date.month)
			sum_days = sum_days + days_in_month

			if i == 2:
				avg_day_salary_3_month = sum_salary / sum_days

			if i == 5:
				avg_day_salary_6_month = sum_salary / sum_days

			curr_pay_date = curr_pay_date - relativedelta(months=1) # loop --

		avg_day_salary = max(avg_day_salary_3_month, avg_day_salary_6_month)
		maternity_pay = avg_day_salary * WEEKS_BIRTH_SALARY * 7
		maternity_pay = round_by_factor(maternity_pay, 500)

		maternity_pay_event = DateEvent(event_type="income", 
			                   category="MATERNITY_PAYS", 
			                   name="maternity pay "+ child.name, 
			                   event_sum=maternity_pay,
			                   start=child.birthday_billing_date,
			                   end=child.birthday_billing_date,
			                   person_type = child.type)

		maternity_pay_event.split()


		### update birth grant

		maternity_grant_event = DateEvent(event_type="income", 
			                   category="MATERNITY_PAYS", 
			                   name="maternity grant "+ child.name, 
			                   event_sum=get_maternity_grant(child_order),
			                   start=child.birthday_billing_date,
			                   end=child.birthday_billing_date,
			                   person_type = child.type)

		maternity_grant_event.split()

		### update child allowance

		child_allowance_event = DateEvent(event_type="income", 
			                   category="MATERNITY_PAYS", 
			                   name="child allowance "+ child.name, 
			                   event_sum=get_child_allowance(child_order),
			                   start=child.birthday_billing_date,
			                   end=child.birthday_billing_date + relativedelta(years=18),
			                   period=1,
			                   person_type=child.type)

		child_allowance_event.split()



# Write the csv output file
def write_cash_flow(csv_file_name):
	with open(csv_file_name, 'w', newline='') as csvfile:
		writer = csv.writer(csvfile)

		header_row = ['DATE', 'INCOMES', 'EXPENSES', 'BALANCE', 'BANK']

		# incomes first, then expenses

		for event_type in Config.event_types:
			for category in categories[event_type]:
				header_row.append(category)

		writer.writerow(header_row)

		dates = sorted(months.keys()) # key is date object 

		bank_acc = Config.initial_saving
		expenses = 0
		incomes = 0

		for date_obj in dates:

			curr_month = months[date_obj]

			
			if write_detailed_month and date_obj == detailed_month:
				write_detailed_month_csv(date_obj, curr_month)

			incomes  =  curr_month.agg_sums["income"]
			expenses =  curr_month.agg_sums["expense"]

			bank_acc = bank_acc + incomes - expenses

			row = [date_obj,incomes,expenses, (incomes-expenses), bank_acc]

			for event_type in Config.event_types:
				for category in categories[event_type]:
					category_sum = curr_month.agg_categories.get(category)
					if category_sum is not None:
						row.append(category_sum)
					else:
						row.append(0)

			writer.writerow(row)


def write_detailed_month_csv(date_obj, month):
	print (date_obj)
	with open(str(date_obj) + ".csv", 'w', newline='') as csvfile:
		writer = csv.writer(csvfile)
		writer.writerow(MonthEvent.generate_header_row())		
		for event in month.month_events:
			writer.writerow(event.generate_row())


	



# TESTERS

def test_persons_load():
	load_persons('persons.csv')	
	for person in persons:
		print (person)

def dates_tester():

	bitrh_date = datetime.strptime("14/07/1983", Config.format_str).date()
	

	from_age = 37
	to_age   = 37

	start_date= bitrh_date + relativedelta(years=from_age)
	end_date = bitrh_date + relativedelta(years=to_age)

	print (start_date)
	print (end_date)



class ChildcareType:
	DAYCARE=1
	KINDERGARDEN_ZAHARON=2
	SCHOOL_ZAHARON=3
	POST_CHILDCARE=4

childcare_costs = {
	ChildcareType.DAYCARE: 3000,
	ChildcareType.KINDERGARDEN_ZAHARON: 1000,
	ChildcareType.SCHOOL_ZAHARON: 800,
	ChildcareType.POST_CHILDCARE: 0}

class EducationAges:
	GAN_HOVA=3
	KITA_ALEF=6
	KITA_DALET=9


def get_childcare_type(child, school_year):

	end_of_civil_year = school_year.replace(month=12, day=31)
	child_age_at_end_of_year = relativedelta(end_of_civil_year, child.birthday_actual_date)

	if child_age_at_end_of_year.years >= EducationAges.KITA_DALET:
		return ChildcareType.POST_CHILDCARE

	if child_age_at_end_of_year.years >= EducationAges.KITA_ALEF:
		return ChildcareType.SCHOOL_ZAHARON

	if child_age_at_end_of_year.years >= EducationAges.GAN_HOVA:
		return ChildcareType.KINDERGARDEN_ZAHARON

	return ChildcareType.DAYCARE


def create_childcare_events():

	MATERNITY_LEAVE_WEEKS = 26

	children = [person for person in persons if person.type == "child"]

	for child in children:

		daycare_period = Period()
		kindergarden_zaharon_period = Period()
		school_zaharon_period = Period()

		maternity_leave_end = child.birthday_actual_date + relativedelta(weeks=MATERNITY_LEAVE_WEEKS)

		# daycare

		daycare_period.start = maternity_leave_end.replace(day=1)
		curr_school_year = get_next_school_year_start(maternity_leave_end)
		curr_childcare_type = get_childcare_type(child, curr_school_year)

		while curr_childcare_type == ChildcareType.DAYCARE:
			daycare_period.end = curr_school_year + relativedelta(years=1, months=-1) # 01.08.XXXX
			curr_school_year += relativedelta(years=1)
			curr_childcare_type = get_childcare_type(child, curr_school_year) 

		# garden zaharon

		kindergarden_zaharon_period.start = curr_school_year

		while curr_childcare_type == ChildcareType.KINDERGARDEN_ZAHARON:
			kindergarden_zaharon_period.end = curr_school_year + relativedelta(years=1, months=-1) # 01.08.XXXX
			curr_school_year += relativedelta(years=1)
			curr_childcare_type = get_childcare_type(child, curr_school_year)

		# school zaharon

		school_zaharon_period.start = curr_school_year

		while curr_childcare_type == ChildcareType.SCHOOL_ZAHARON:
			school_zaharon_period.end = curr_school_year + relativedelta(years=1, months=-1) # 01.08.XXXX
			curr_school_year += relativedelta(years=1)
			curr_childcare_type = get_childcare_type(child, curr_school_year)

	 
		daycare_event = DateEvent(event_type="expense", 
		                   category="DAYCARE", 
		                   name="childcare pay"+ child.name, 
		                   event_sum=childcare_costs[ChildcareType.DAYCARE],
		                   start=daycare_period.start,
		                   end=daycare_period.end,
		                   period=1,
		                   person_type = child.type)
		daycare_event.split()

		daycare_event = DateEvent(event_type="expense", 
		                   category="KINDERGARDEN_ZAHARON", 
		                   name="childcare pay"+ child.name, 
		                   event_sum=childcare_costs[ChildcareType.KINDERGARDEN_ZAHARON],
		                   start=kindergarden_zaharon_period.start,
		                   end=kindergarden_zaharon_period.end,
		                   period=1,
		                   person_type = child.type)

		daycare_event.split()

		daycare_event = DateEvent(event_type="expense", 
		                   category="SCHOOL_ZAHARON", 
		                   name="childcare pay"+ child.name, 
		                   event_sum=childcare_costs[ChildcareType.SCHOOL_ZAHARON],
		                   start=school_zaharon_period.start,
		                   end=school_zaharon_period.end,
		                   period=1,
		                   person_type = child.type)

		daycare_event.split()

def create_children_tax_points_events():
	
	TAX_POINT_VALUE = 220

	children = [person for person in persons if person.type == "child"]

	print (children)

	for child in children:

		birth_year = child.birthday_actual_date.year
		birth_month = child.birthday_actual_date.month

		# one-time tax reduce calculated for January
		curr_event = DateEvent(event_type="income", 
                   category="TAX_POINTS", 
                   name="tax point "+ child.name, 
                   event_sum=birth_month*TAX_POINT_VALUE,
                   start=datetime(day=1, month=birth_month, year=birth_year).date(),
                   end=datetime(day=1, month=birth_month, year=birth_year).date(),
                   period=1,
                   person_type = child.type)
		curr_event.split()


		if birth_month <= 11:
			curr_event = DateEvent(event_type="income", 
	                   category="TAX_POINTS", 
	                   name="tax point "+ child.name, 
	                   event_sum=3*TAX_POINT_VALUE,
	                   start=datetime(day=1, month=birth_month+1, year=birth_year).date(),
	                   end=datetime(day=1, month=12, year=birth_year).date(),
	                   period=1,
	                   person_type = child.type)
			curr_event.split()

		curr_event = DateEvent(event_type="income", 
                   category="TAX_POINTS", 
                   name="tax point "+ child.name, 
                   event_sum=5*TAX_POINT_VALUE,
                   start=datetime(day=1, month=1, year=birth_year+1).date(),
                   end=datetime(day=1, month=12, year=birth_year+5).date(),
                   period=1,
                   person_type = child.type)
		curr_event.split()

		curr_event = DateEvent(event_type="income", 
                   category="TAX_POINTS", 
                   name="tax point "+ child.name, 
                   event_sum=1*TAX_POINT_VALUE,
                   start=datetime(day=1, month=1, year=birth_year+6).date(),
                   end=datetime(day=1, month=12, year=birth_year+17).date(),
                   period=1,
                   person_type = child.type)
		curr_event.split()

		curr_event = DateEvent(event_type="income", 
                   category="TAX_POINTS", 
                   name="tax point "+ child.name, 
                   event_sum=0.5*TAX_POINT_VALUE,
                   start=datetime(day=1, month=1, year=birth_year+18).date(),
                   end=datetime(day=1, month=12, year=birth_year+18).date(),
                   period=1,
                   person_type = child.type)
		curr_event.split()



def calc_childcare_cost(birthday):


	# MATERNITY_LEAVE_WEEKS = 26
	MATERNITY_LEAVE_WEEKS = 15
	SMALL_PAY = 2192
	BIG_PAY = 2857

	# SMALL_PAY=913
	# BIG_PAY=1133

	PRIVATE_CHILDCARE_DAY_PAY = 200


	maternity_leave           = Period(start=birthday, weeks=MATERNITY_LEAVE_WEEKS) 

	childcare_summer_vacation_start = datetime(day=8, month=8, year=maternity_leave.end.year).date()
	childcare_summer_vacation_end = childcare_summer_vacation_start.replace(day=30)


	childcare_summer_vacation = Period(start=childcare_summer_vacation_start, end=childcare_summer_vacation_end)

	# number of days of maternity_leave in childcare_summer_vacation
	# private_day_care_cost = PRIVATE_CHILDCARE_DAY_PAY*childcare_summer_vacation.days()
	# if childcare_summer_vacation.is_overlap(maternity_leave):

	# 	childcare_summer_vacation_maternity_leave_overlap = childcare_summer_vacation.get_overlap(maternity_leave)

	# 	private_day_care_days = childcare_summer_vacation.days() - childcare_summer_vacation_maternity_leave_overlap.days()

	# 	private_day_care_cost = private_day_care_days * PRIVATE_CHILDCARE_DAY_PAY


	childcare_start_pay = maternity_leave.end.replace(day=1)

	curr_childcare_year_start = get_next_school_year_start(maternity_leave.end)
	


	childcare_start_reduced_pay = copy.deepcopy(curr_childcare_year_start)

	# check if the child is older than 1 year at the start of the school year
	curr_child_age = relativedelta(curr_childcare_year_start,birthday)
	if (curr_child_age.years*12 + curr_child_age.months) < 15:
		childcare_start_reduced_pay += relativedelta(years=1)

	curr_childcare_year_start = copy.deepcopy(childcare_start_reduced_pay)

	while True:

		end_of_calendar_curr_year = curr_childcare_year_start.replace(day=31,month=12)

		curr_child_age = relativedelta(end_of_calendar_curr_year, birthday)
		if curr_child_age.years > 3:
			break

		final_childcare_year_start = curr_childcare_year_start
		curr_childcare_year_start += relativedelta(years=1)

	childcare_end_pay = final_childcare_year_start + relativedelta(years=1,months=-1)


	#cost calculation

	big_pay_duration = relativedelta(childcare_start_reduced_pay, childcare_start_pay)
	big_pay_cost = (big_pay_duration.years*12 + big_pay_duration.months)*BIG_PAY


	small_pay_duration = relativedelta(childcare_end_pay, childcare_start_reduced_pay)
	small_pay_cost = (small_pay_duration.years*12 + small_pay_duration.months)*SMALL_PAY

	# return private_day_care_cost + big_pay_cost + small_pay_cost
	return big_pay_cost + small_pay_cost

def calc_child_cost():

	mom_salary = 11000
	from_age = 0
	upto_age = 18

	child_file = Config.proj_dir + '/input_files/child.csv'





def run():

	# load config
	Config.proj_dir = sys.argv[1]
	Config.read_file()
	
	# load data and create events
	load_date_events(Config.proj_dir +'/input_files/date_events.csv')
	load_persons(Config.proj_dir + '/input_files/persons.csv')
	load_mortgage(Config.proj_dir + '/input_files/mortgage.csv')
	
	# auto generate events for children
	update_incomces_after_births()
	create_childcare_events()
	create_children_tax_points_events()

	# wirte ouptup to file
	write_cash_flow(Config.proj_dir + '/cash_flow.csv')







if __name__ == '__main__':
	run()



