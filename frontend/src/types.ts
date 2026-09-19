export type Unit = {
  unit_id: string
  code: string
  display_name: string
  legal_name: string
  tax_code: string
  address: string
  signatory_display: string
  signatory_title: string
  production_ready: boolean
}

export type Position = {
  position_id: string
  title: string
  role_label: string
  base_wage: string
}

export type SalaryMode = 'gross' | 'net'

export type WorkSchedule = {
  weekdays_label: string
  weekday_morning: string
  weekday_afternoon: string
  saturday_label: string
  saturday_morning: string
  saturday_afternoon: string
  weekday_lunch: string
  saturday_lunch: string
}

export type ContractForm = {
  unit_id: string
  employee: {
    full_name: string
    code: string
    birth_date: string
    gender: string
    nationality: string
    identity_number: string
    identity_issue_date: string
    identity_issuer: string
    permanent_address: string
  }
  job: { position_id: string }
  signing_date: string
  contract: { type_term_text: string; end_date: string }
  salary_period: { effective_from: string; effective_to: string }
  responsibility: {
    commitment_from: string
    commitment_to: string
    liability_from: string
    liability_to: string
  }
  compensation: {
    insurance_base: string
    employer_union_base: string
    employee_union_base: string
    pit_withheld: string
    salary_mode: SalaryMode
    salary_amount: string
  }
  work_schedule: WorkSchedule
  payment: { window_text: string }
}

export type Calculation = {
  base_wage: string
  position_allowance: string
  gross_income: string
  net_income: string
  employee_insurance: string
  employee_union: string
  pit_withheld: string
  employer_insurance: string
  employer_union: string
  employer_total_cost: string
}

export type PreviewResponse = {
  demo_only: boolean
  unit_id: string
  calculation: Calculation
  policy_status: string
  notice: string
}
