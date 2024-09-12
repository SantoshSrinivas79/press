# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import boto3
import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.utils import flt


AWS_HOURS_IN_A_MONTH = 730


class AWSSavingsPlanRecommendation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		generated_at: DF.Datetime | None
		hourly_commitment: DF.Currency
		hourly_on_demand_spend: DF.Currency
		lookback_period: DF.Data | None
		monthly_commitment: DF.Currency
		monthly_on_demand_spend: DF.Currency
		monthly_savings_amount: DF.Currency
		name: DF.Int | None
		payment_option: DF.Data | None
		roi_percentage: DF.Float
		savings_percentage: DF.Float
		savings_plan_type: DF.Data | None
		term: DF.Data | None
		upfront_cost: DF.Currency
	# end: auto-generated types

	pass

	def before_insert(self):
		response = self.get_recommendation()

		self.generated_at = frappe.utils.convert_utc_to_system_timezone(
			frappe.utils.get_datetime(response["Metadata"]["GenerationTimestamp"])
		).replace(tzinfo=None)

		recommendation = response["SavingsPlansPurchaseRecommendation"]
		self.lookback_period = recommendation["LookbackPeriodInDays"]
		self.payment_option = recommendation["PaymentOption"]
		self.term = recommendation["TermInYears"]
		self.savings_plan_type = recommendation["SavingsPlansType"]

		details = recommendation["SavingsPlansPurchaseRecommendationDetails"][0]

		self.currency = details["CurrencyCode"]
		self.upfront_cost = details["UpfrontCost"]

		self.hourly_commitment = flt(details["HourlyCommitmentToPurchase"])
		self.monthly_commitment = self.hourly_commitment * AWS_HOURS_IN_A_MONTH

		self.savings_percentage = flt(details["EstimatedSavingsPercentage"])
		self.hourly_on_demand_spend = flt(details["CurrentAverageHourlyOnDemandSpend"])
		self.monthly_on_demand_spend = self.hourly_on_demand_spend * AWS_HOURS_IN_A_MONTH
		self.monthly_savings_amount = (
			self.monthly_on_demand_spend * self.savings_percentage / 100
		)

		self.roi_percentage = self.monthly_savings_amount / self.monthly_commitment * 100

	def validate(self):
		self.validate_duplicate()

	@property
	def client(self):
		settings = frappe.get_single("Press Settings")
		client = boto3.client(
			"ce",
			region_name="us-east-1",
			aws_access_key_id=settings.aws_access_key_id,
			aws_secret_access_key=settings.get_password("aws_secret_access_key"),
		)
		return client

	def generate_recommendation(self):
		self.client.start_savings_plans_purchase_recommendation_generation()

	def get_recommendation(self):
		response = self.client.get_savings_plans_purchase_recommendation(
			SavingsPlansType="COMPUTE_SP",
			TermInYears="THREE_YEARS",
			PaymentOption="NO_UPFRONT",
			LookbackPeriodInDays="SEVEN_DAYS",
		)
		return response

	def validate_duplicate(self):
		if frappe.db.exists(
			self.doctype,
			{
				"generated_at": self.generated_at,
			},
		):
			frappe.throw(
				"AWS Savings Plan Recommendation witht this timestamp already exists",
				frappe.DuplicateEntryError,
			)


def refresh():
	frappe.new_doc("AWS Savings Plan Recommendation").generate_recommendation()


def create():
	try:
		frappe.new_doc("AWS Savings Plan Recommendation").insert()
	except frappe.DuplicateEntryError:
		pass
	except Exception:
		# Ignore all exceptions till this works
		pass