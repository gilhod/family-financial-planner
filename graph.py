import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date
from dateutil.relativedelta import relativedelta



def example():
	x = np.linspace(0, 10, 500)
	y = np.sin(x)

	fig, ax = plt.subplots()

	# Using set_dashes() to modify dashing of an existing line
	line1, = ax.plot(x, y, label='Using set_dashes()')
	line1.set_dashes([2, 2, 10, 2])  # 2pt line, 2pt break, 10pt line, 2pt break

	# Using plot(..., dashes=...) to set the dashing when creating a line
	line2, = ax.plot(x, y - 0.2, dashes=[6, 2], label='Using the dashes parameter')

	ax.legend()
	plt.show()



format_str = '%Y-%m-%d'
birth_gil = datetime.strptime("1983-07-14", format_str).date()

def create_single_plot(ax, project_dir):
	dates = list()
	bank = list()
	with open(project_dir + "/cash_flow.csv") as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:

			d = datetime.strptime(row['DATE'], format_str).date()
			# print(relativedelta(d,birth_gil))

			# dates.append(datetime.strptime(row['DATE'], format_str).date())

			gil_age_delta = relativedelta(d,birth_gil)
			gil_age = gil_age_delta.years + gil_age_delta.months/12.0 + gil_age_delta.days/365.0
			# print(gil_age)
			dates.append(gil_age)


			# dates.append(relativedelta(d,birth_gil))
			bank.append(float(row['BANK']))

	bank_line, = ax.plot(dates, bank, label=project_dir)


def plot_multiple_graphs(project_dirs):

	fig, ax = plt.subplots()
	ax.grid(axis='y')

	for project_dir in project_dirs:
		 create_single_plot(ax, project_dir)

	ax.legend()
	plt.title('Total')
	plt.show()

def plot_incomes_expenses():
	dates = list()
	incomes = list()
	expenses = list()
	with open("cash_flow.csv") as csv_file:
		reader = csv.DictReader(csv_file)
		for row in reader:
			dates.append(datetime.strptime(row['DATE'], format_str).date())
			incomes.append(float(row['INCOMES']))
			expenses.append(float(row['EXPENSES']))


	# fig, ax = plt.subplots()
	# line1, = ax.plot(dates, incomes, label='incomes')
	# line2, = ax.plot(dates, expenses, label='expenses')

	plt.scatter(dates,incomes, s=3)
	plt.scatter(dates,expenses, s=3)

	axes = plt.gca()
	axes.yaxis.grid()

	# ax.legend()
	plt.title('incomes vs expenses')
	plt.show()



if __name__ == '__main__':
	# plot_incomes_expenses()
	# plot_total()

	plot_multiple_graphs(sys.argv[1:])