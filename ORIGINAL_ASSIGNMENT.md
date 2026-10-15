# ApTap Data Engineer take-home task

Thank you for applying. This task is the third stage of our process.

It should take **about six hours**. Please return it within **five working days** of receiving it.
If you finish the core parts sooner, stop. We would rather see careful work than everything rushed.
If you run out of time, say what you would have done next. That counts.

## The context

ApTap puts offers inside bank apps: bill switching, rewards and discounts.
Our ML suite, Compass, reads a customer's transactions, works out which bills they pay, and spots when they are about to switch or have just switched.
Each bank we work with has 10 to 20 million customers.
At some banks, the data and our models never leave the bank's own environment. At others, we process data on our own AWS.
We also run a data dashboard that shows banks and advertisers how offers perform (funnels, sales, commission). It is built in Python, pandas and MongoDB, and runs on AWS.

You have three months of transactions for 1,500 synthetic customers from one fictional bank, plus a small file of labelled merchant descriptors.
The data is synthetic, but it has the kind of problems real bank feeds have.
Finding them is part of the task.

## The files

| File | What it is |
|---|---|
| `transactions_2026_07.csv` | July transactions |
| `transactions_2026_08.csv` | August transactions |
| `transactions_2026_09.jsonl` | September transactions. The bank migrated platforms in September. |
| `merchant_labels.csv` | Bill category for some merchant descriptors. Labelled by a person, so it may contain mistakes. |

Debits are negative amounts.
Categories: `broadband`, `energy`, `mobile`, `car_insurance`, `home_insurance`, `water`, `streaming`, `gym`, `council_tax`, `not_a_bill`.

## Ground rules

- Write the pipeline in **Python**. Use any store you like: Parquet, DuckDB, SQLite, Postgres or MongoDB. If it needs a server, include a `docker-compose.yml`.
- Use any tool for charts and the report.
- Your categoriser must **run offline, with no network calls**. You are welcome to use an LLM while you build it, for example to draft rules or label data. It just can't call one when it runs.
- Every figure you report must be traceable back to the raw files.

## What to build

### Part A. Pipeline: ingest, clean, store (about 2 hours)

Load all three files into one clean transactions table.

1. **One command runs everything**, for example `python -m pipeline data/`. Tell us the exact command in your README.
2. **Keep three layers**: the raw data as you received it, the clean table, and a `rejected_rows.csv` holding every row that did not make it into the clean table, with a reason for each.
3. **Output `clean_transactions.csv`** with columns `transaction_id, customer_id, booking_date (YYYY-MM-DD), amount, description`.
4. **Reconcile.** Rows in must equal clean rows plus rejected rows. Print or write that check every run.
5. **Write two data-quality checks as code.** They should fail loudly, or report clearly, when something is wrong with an incoming file.
6. **Re-runs.** After you submit, we will run your pipeline again with one more file, `transactions_2026_10.jsonl`, in the same schema as September. The bank may add new fields or vary the formatting. Your pipeline must load the new data, cope with rows it has already seen, and not create duplicates. Tell us exactly how to run it with an extra file.
7. **Measure it.** Each run should report how long it took and its peak memory use.

Every decision you make about what to drop, merge or fix should be explainable.

### Part B. Features: categories, bills and switches (about 1.5 hours)

1. **Categoriser.** It takes a CSV with a `description` column and writes the same CSV with a `category` column added. It runs as one command, for example `python -m categorise input.csv output.csv`. We will run it on descriptors you have not seen.
2. **`recurring_bills.csv`**: one row per bill a customer is paying at the end of September.
   Columns: `customer_id, merchant, category, cadence, typical_amount, next_expected_date`.
3. **`switches.csv`**: customers who moved provider within a category during the period.
   Columns: `customer_id, category, old_merchant, new_merchant, first_month_with_new`.

Write the bill and switch logic in SQL, or in Python a reviewer can follow step by step.

### Part C. Analysis and a one-page report (about 1.5 hours)

Our bill-switching offers tell customers they could save money.
**From this data, do customers who switch provider pay less afterwards?**
Answer for each category where you can, and say how sure you are.

Produce a one-page report for a commercial reader who is not a data person, for example a partnerships manager at a bank. Any format is fine: HTML, PDF, a notebook, Streamlit, or screenshots of a BI tool. It should include:

- at least one chart
- your numbers with a measure of uncertainty
- a plain-English answer and recommendation
- anything the reader should be careful about

### Part D. Notes (about 1 hour, two pages maximum)

Write `NOTES.md` covering:

1. **What you found wrong with the data**, and what you did about each problem.
2. **What you don't trust** in your own outputs, and why.
3. **Running this in production.** The pipeline and categoriser must run every month in two settings:
   - **On ApTap's AWS**, for banks that send us their data.
   - **Inside a bank**: 15 million customers, monthly files, no data can leave the bank's environment, you cannot install arbitrary software, and every release goes through the bank's change control. As volumes grow, file uploads into the bank's environment start timing out.

   Sketch both. What would you change in your design, and what would you do in your first week? Include:
   - **Scale.** Use the runtime and memory you measured to estimate what a 15-million-customer month needs, and say what breaks first.
   - **Storage.** How you would model, partition and index the data at that size.
   - **Personal data.** What personal data is in these files, and how you would handle it: access, retention, and what may and may not leave each environment.
   - **Monitoring and cost.** How you would know if the categoriser started getting worse, and what it would cost per million transactions.
4. **How you used AI tools.** A short summary. The full chats go in your submission (see below).

## Your AI chats

We encourage AI tools, and we want to see how you used them.
**Include every LLM conversation you had while doing this task.** A submission without them is incomplete.

- **Chat apps** (Claude, ChatGPT, Gemini and similar): send a share link that opens the full conversation. Please also include an exported copy (PDF, Markdown or text), because links can expire.
- **Coding agents and IDE assistants** (Claude Code, Codex, Cursor, Copilot Chat and similar): export the session history or transcript files for this task and include them in the repository or zip. Use whatever export your tool provides.
- **If you did not use AI**, say so in `NOTES.md`.

## What to send back

A Git repository link or a zip containing:

- your code, with a short section in the README on how to run it end to end, including with an extra file. A Git repository with your real commit history is preferred over a zip.
- `clean_transactions.csv`, `rejected_rows.csv`, `recurring_bills.csv`, `switches.csv`
- your report (Part C)
- `NOTES.md`
- your AI chats

## How we assess it

In order of importance:

1. Whether your cleaning and features are right.
2. Whether your pipeline runs first time, re-runs safely and could go into production.
3. Whether your analysis and report are sound and honest about uncertainty.
4. Whether your notes show good judgement about data you can't fully trust.

A shorter submission with honest notes beats a longer one that hides its gaps.

Questions about the task: reply to the email it came with. Asking a clarifying question counts in your favour. We give the same answer to every candidate who asks the same question.
