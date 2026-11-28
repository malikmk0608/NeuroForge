const expenses = [
  { reference: 'EXP-021', description: 'Team travel', amount: 2400, status: 'In review' },
  { reference: 'EXP-022', description: 'Office supplies', amount: 850, status: 'Reimbursed' },
]
const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

export default function FinanceExpense() {
  return <section className="card app-content">
    <h2>Expense ledger</h2>
    <p className="app-caption">Sample expense reports</p>
    <ul className="app-rows">{expenses.map(expense => <li key={expense.reference}>
      <div><small>{expense.reference}</small><strong>{expense.description}</strong></div>
      <div><strong>{currency.format(expense.amount)}</strong><span>{expense.status}</span></div>
    </li>)}</ul>
  </section>
}
