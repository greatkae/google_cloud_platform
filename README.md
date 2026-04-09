# Cstore Analytics Dashboard

A Streamlit dashboard for analyzing convenience store data across five Idaho locations.

## Links
- **GitHub Repository:** https://github.com/greatkae/google_cloud_platform
- **Live App (Cloud Run):** https://cstore-dashboard-37259924741.us-west1.run.app

## Running Locally with Docker
Clone the repo and run:
```bash
docker compose up
```
Then open your browser to `http://localhost:8080`

## App Pages
| Page | Question Addressed |
|------|-------------------|
| Top 5 Products | What are the top 5 weekly sellers excluding fuel? |
| Packaged Beverages | Which beverage brands should be dropped? |
| Cash vs Credit | How do cash and credit customers compare? |
| Demographics | What do customer demographics look like by store area? |

---

## Vocabulary Challenge

### 1. The Added Value of Databricks

Databricks lets you work with massive datasets that would crash or choke a 
local machine. It runs on a cluster, so instead of waiting forever for your 
laptop to process 100 million rows, Databricks handles it in minutes.

For this project, I used it to query and aggregate raw transaction data before 
bringing it into the dashboard. Without it, that step would not have been 
possible locally.

| Stage | Tool | Purpose |
|-------|------|---------|
| Raw Storage | Unity Catalog | Store the full dataset |
| Processing | PySpark on Databricks | Aggregate and clean |
| Dashboard | Streamlit + Polars | Visualize and explore |

The real value is that it sits at the start of your pipeline and handles the 
work that nothing else reasonably can.

---

### 2. PySpark vs Polars

They both process tabular data but they are built for completely different 
situations.

| Feature | PySpark | Polars |
|---------|---------|--------|
| Scale | Billions of rows across a cluster | Millions of rows on one machine |
| Speed | Fast at scale, slow to start | Very fast locally |
| Syntax | Verbose | Clean and concise |
| Setup | Needs a cluster | Just pip install |
| Best for | Big data pipelines | Local analytics and dashboards |

PySpark is the right tool when your data is too big for one machine. Polars is 
the right tool when it is not. For this project I used both -- Databricks and 
PySpark to process the raw data, then Polars in the dashboard to filter and 
transform it on the fly.

---

### 3. Docker Explained

Say you build an app on your laptop and it works perfectly. Then your professor 
tries to run it and gets a bunch of errors because they have a different version 
of Python or are missing a library you forgot to mention.

Docker fixes that. It packages your app along with everything it needs to run 
into one container. Anyone with Docker can run that container and get the exact 
same result, regardless of their machine or setup.

For this project it means my professor can run the full dashboard locally with 
one command without installing anything else. It also made deploying to the 
cloud straightforward since Cloud Run just runs the same container.

---

### 4. GCP vs AWS

| Category | GCP | AWS |
|----------|-----|-----|
| Cost | Competitive, per-second billing | Similar, but pricing is harder to follow |
| Free Tier | $300 credits for new users | 12 months free on select services |
| Ease of Use | Clean and straightforward | More powerful but steeper learning curve |
| Serverless Containers | Cloud Run | App Runner / Elastic Beanstalk |
| Best for | Data and ML workloads | Broadest service catalog, enterprise use |

For a project like this GCP is the better choice. Cloud Run made deployment 
simple and the student credits covered everything. AWS has more services overall 
but can be overwhelming when you just need to ship something.

---

### 5. A Poem

Raw data sitting in a warehouse,
too big to touch with normal tools.
We sparked it up on Databricks,
and learned to play by different rules.

Cleaned it up and built a dashboard,
wrapped the whole thing in a box.
Pushed it live on Google Cloud,
and finally took the training wheels off.