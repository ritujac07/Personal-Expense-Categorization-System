
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import date, datetime

DB = "expenses.db"
CATEGORIES = [
    "Food", "Travel", "Shopping", "Education",
    "Bills", "Healthcare", "Entertainment", "Other"
]

def connect():
    return sqlite3.connect(DB)

def setup():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                description TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS budgets(
                month TEXT PRIMARY KEY,
                amount REAL NOT NULL
            )
        """)

def clear_form():
    amount_entry.delete(0, tk.END)
    category_box.set("Food")
    date_entry.delete(0, tk.END)
    date_entry.insert(0, date.today().isoformat())
    description_entry.delete(0, tk.END)

def get_data():
    try:
        amount = float(amount_entry.get())
        category = category_box.get()
        expense_date = date_entry.get().strip()
        description = description_entry.get().strip()

        if amount <= 0 or category not in CATEGORIES:
            raise ValueError

        datetime.strptime(expense_date, "%Y-%m-%d")
        return amount, category, expense_date, description

    except ValueError:
        messagebox.showerror(
            "Invalid input",
            "Enter a positive amount and date as YYYY-MM-DD."
        )
        return None

def add_expense():
    data = get_data()
    if data is None:
        return

    with connect() as db:
        db.execute("""
            INSERT INTO expenses(amount, category, expense_date, description)
            VALUES(?, ?, ?, ?)
        """, data)

    messagebox.showinfo("Success", "Expense added!")
    clear_form()
    view_expenses()

def view_expenses(records=None):
    for item in table.get_children():
        table.delete(item)

    if records is None:
        with connect() as db:
            records = db.execute("""
                SELECT * FROM expenses
                ORDER BY expense_date DESC, id DESC
            """).fetchall()

    for row in records:
        table.insert("", tk.END, values=row)

    update_summary()

def search_expenses():
    keyword = search_entry.get().strip()

    with connect() as db:
        records = db.execute("""
            SELECT * FROM expenses
            WHERE category LIKE ? OR description LIKE ?
            ORDER BY expense_date DESC
        """, ("%" + keyword + "%", "%" + keyword + "%")).fetchall()

    view_expenses(records)

def select_row(event=None):
    selected = table.selection()
    if not selected:
        return

    row = table.item(selected[0], "values")
    clear_form()
    amount_entry.insert(0, row[1])
    category_box.set(row[2])
    date_entry.delete(0, tk.END)
    date_entry.insert(0, row[3])
    description_entry.insert(0, row[4] or "")

def update_expense():
    selected = table.selection()
    if not selected:
        messagebox.showwarning("Select", "Select an expense from the table.")
        return

    data = get_data()
    if data is None:
        return

    expense_id = table.item(selected[0], "values")[0]

    with connect() as db:
        db.execute("""
            UPDATE expenses
            SET amount=?, category=?, expense_date=?, description=?
            WHERE id=?
        """, (*data, expense_id))

    messagebox.showinfo("Success", "Expense updated!")
    clear_form()
    view_expenses()

def delete_expense():
    selected = table.selection()
    if not selected:
        messagebox.showwarning("Select", "Select an expense from the table.")
        return

    expense_id = table.item(selected[0], "values")[0]

    if messagebox.askyesno("Confirm", "Delete this expense?"):
        with connect() as db:
            db.execute("DELETE FROM expenses WHERE id=?", (expense_id,))

        clear_form()
        view_expenses()
        messagebox.showinfo("Success", "Expense deleted!")

def set_budget():
    try:
        amount = float(budget_entry.get())
        if amount <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid", "Enter a budget greater than zero.")
        return

    month = date.today().strftime("%Y-%m")

    with connect() as db:
        db.execute("""
            INSERT OR REPLACE INTO budgets(month, amount) VALUES(?, ?)
        """, (month, amount))

    budget_entry.delete(0, tk.END)
    update_summary()
    messagebox.showinfo("Success", "Budget saved!")

def update_summary():
    month = date.today().strftime("%Y-%m")

    with connect() as db:
        total = db.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses WHERE expense_date LIKE ?
        """, (month + "%",)).fetchone()[0]

        result = db.execute(
            "SELECT amount FROM budgets WHERE month=?", (month,)
        ).fetchone()

    budget = result[0] if result else 0
    remaining = budget - total

    summary.config(
        text=f"This month: ₹{total:.2f}\n"
             f"Budget: ₹{budget:.2f} | Remaining: ₹{remaining:.2f}"
    )

def monthly_report():
    month = date.today().strftime("%Y-%m")

    with connect() as db:
        records = db.execute("""
            SELECT category, SUM(amount)
            FROM expenses
            WHERE expense_date LIKE ?
            GROUP BY category
            ORDER BY SUM(amount) DESC
        """, (month + "%",)).fetchall()

    report = tk.Toplevel(root)
    report.title("Monthly Report")
    report.geometry("320x400")

    tk.Label(
        report, text="Category-wise Report",
        font=("Arial", 15, "bold")
    ).pack(pady=10)

    if not records:
        tk.Label(report, text="No expenses this month.").pack()
        return

    for category, amount in records:
        tk.Label(
            report, text=f"{category}: ₹{amount:.2f}",
            font=("Arial", 12)
        ).pack(anchor="w", padx=20, pady=4)

# Main window
setup()
root = tk.Tk()
root.title("Personal Expense Tracker")
root.geometry("380x780")

tk.Label(
    root, text="PERSONAL EXPENSE TRACKER",
    font=("Arial", 15, "bold"), fg="blue"
).pack(pady=8)

# Scrollable main content
outer = tk.Frame(root)
outer.pack(fill="both", expand=True)

canvas = tk.Canvas(outer, highlightthickness=0)
scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

content = tk.Frame(canvas, padx=8, pady=5)
window_id = canvas.create_window((0, 0), window=content, anchor="nw")

def resize_content(event):
    canvas.itemconfigure(window_id, width=event.width)

def update_scroll(event=None):
    canvas.configure(scrollregion=canvas.bbox("all"))

content.bind("<Configure>", update_scroll)
canvas.bind("<Configure>", resize_content)

# Expense form
form = tk.LabelFrame(content, text="Expense Details", padx=8, pady=8)
form.pack(fill="x", pady=5)

tk.Label(form, text="Amount (₹)").pack(anchor="w")
amount_entry = tk.Entry(form, font=("Arial", 12))
amount_entry.pack(fill="x", pady=3)

tk.Label(form, text="Category").pack(anchor="w")
category_box = ttk.Combobox(
    form, values=CATEGORIES, state="readonly", font=("Arial", 12)
)
category_box.pack(fill="x", pady=3)
category_box.set("Food")

tk.Label(form, text="Date (YYYY-MM-DD)").pack(anchor="w")
date_entry = tk.Entry(form, font=("Arial", 12))
date_entry.pack(fill="x", pady=3)
date_entry.insert(0, date.today().isoformat())

tk.Label(form, text="Description").pack(anchor="w")
description_entry = tk.Entry(form, font=("Arial", 12))
description_entry.pack(fill="x", pady=3)

# Buttons in two columns
buttons = tk.Frame(content)
buttons.pack(fill="x", pady=5)

actions = [
    ("Add Expense", add_expense),
    ("Update Selected", update_expense),
    ("Delete Selected", delete_expense),
    ("Clear Form", clear_form),
    ("View All", lambda: view_expenses()),
    ("Monthly Report", monthly_report)
]

for i, (text, command) in enumerate(actions):
    tk.Button(
        buttons, text=text, command=command,
        font=("Arial", 10), height=2
    ).grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)

buttons.columnconfigure(0, weight=1)
buttons.columnconfigure(1, weight=1)

# Search
search_frame = tk.LabelFrame(content, text="Search", padx=8, pady=8)
search_frame.pack(fill="x", pady=5)

search_entry = tk.Entry(search_frame, font=("Arial", 12))
search_entry.pack(fill="x", pady=4)

tk.Button(
    search_frame, text="Search by Category or Description",
    command=search_expenses
).pack(fill="x", pady=3)

tk.Button(
    search_frame, text="Reset Search",
    command=lambda: (search_entry.delete(0, tk.END), view_expenses())
).pack(fill="x", pady=3)

# Budget
budget_frame = tk.LabelFrame(content, text="Monthly Budget", padx=8, pady=8)
budget_frame.pack(fill="x", pady=5)

budget_entry = tk.Entry(budget_frame, font=("Arial", 12))
budget_entry.pack(fill="x", pady=4)

tk.Button(
    budget_frame, text="Set Budget", command=set_budget
).pack(fill="x")

summary = tk.Label(
    content, text="", font=("Arial", 11, "bold"),
    wraplength=330, justify="center"
)
summary.pack(fill="x", pady=8)

# Expense table
table_frame = tk.LabelFrame(content, text="Expense Records", padx=3, pady=3)
table_frame.pack(fill="x", pady=5)

columns = ("ID", "Amount", "Category", "Date", "Description")
table = ttk.Treeview(
    table_frame, columns=columns, show="headings", height=7
)

for col in columns:
    table.heading(col, text=col)
    table.column(col, width=100, minwidth=80, stretch=False)

vertical = ttk.Scrollbar(
    table_frame, orient="vertical", command=table.yview
)
horizontal = ttk.Scrollbar(
    table_frame, orient="horizontal", command=table.xview
)

table.configure(
    yscrollcommand=vertical.set,
    xscrollcommand=horizontal.set
)

table.grid(row=0, column=0, sticky="nsew")
vertical.grid(row=0, column=1, sticky="ns")
horizontal.grid(row=1, column=0, sticky="ew")

table_frame.columnconfigure(0, weight=1)
table.bind("<<TreeviewSelect>>", select_row)

view_expenses()
root.mainloop()		