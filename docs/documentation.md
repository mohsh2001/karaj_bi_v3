# Karaj Bi — Used Car Price Intelligence


## **Title Page & Authors**

**Project:** Karaj Bi — Used Car Price Intelligence for the Jordanian Market

**Author:** _[Your name]_

**Institution / Program:** _[Add institution / course]_

**Date:** _[Add submission date]_


## **Table of Content**

1. Abstract
2. Acknowledgment
3. Business Intelligence Project Description and Objectives
4. Data Research and Acquiring Effort
5. Data Description and Understanding
6. Data Primary Cleaning and Transformation
7. Data Visualization and Insights
8. Dashboard Design & Business Insights
9. Advanced Analytics and AI Modeling
10. Tools Research and Selection Effort
11. Project Deployment Effort – Use Case
12. Results
13. References


## **Abstract**

_[Add abstract]_


## **Acknowledgment**

_[Add acknowledgment]_


## **Business Intelligence Project Description and Objectives**

_[Add project description and objectives]_


## **Data Research and Acquiring Effort**

### Data Source

The dataset for the Karaj Bi project was acquired through web scraping of **OpenSooq Jordan** (`jo.opensooq.com`), the largest classifieds marketplace in Jordan. The "Cars for Sale" section was selected as the primary source, as it contains live, user-submitted listings that reflect the actual Jordanian used-car market — including pricing, vehicle specifications, condition, and seller location.

OpenSooq was chosen over alternative sources for several reasons:

- **Market representativeness** — it is the dominant platform for used-car transactions in Jordan, providing a realistic snapshot of supply and pricing behavior.
- **Listing richness** — each listing exposes structured fields (brand, model, year, mileage, transmission, fuel, etc.) suitable for modeling.
- **Public accessibility** — listings are publicly viewable without authentication.
- **Structured metadata** — pages embed `application/ld+json` schema markup, which provides clean, machine-readable vehicle data without relying on fragile HTML parsing.

### Scraping Approach

A custom asynchronous Python scraper was developed to collect the data efficiently. The pipeline operates in two stages:

**Stage 1 — Listing Discovery (HTTP + JSON-LD parsing)**

- An `aiohttp` client iterates through paginated category pages (`?page=N`) until no further listings are returned.
- Each page is parsed with **BeautifulSoup**, and the embedded `application/ld+json` blocks are extracted.
- The `ItemList` graph nodes yield structured listing objects containing the title, brand, model, year, body type, mileage, price, currency, listing URL, image, and description.

**Stage 2 — Detail Page Enrichment (headless browser)**

- Many fields (trim, seats, transmission, engine size, fuel type, exterior/interior color, body condition, paint, payment method, neighborhood, city) are only exposed after clicking the **"View More"** button on the listing page, which loads additional specifications dynamically.
- To handle this, **Playwright** (headless Chromium) is used. A pool of **10 concurrent browser tabs** processes detail pages in parallel via an `asyncio.Queue`.
- Each worker navigates to the listing, waits for the "View More" button, clicks it to reveal the full specification panel, and then parses the rendered HTML.
- A field-mapping dictionary normalizes raw label text (e.g., `"kilometers"` → `Mileage`, `"car make"` → `Brand`, `"neighborhood"` → `Neighbourhood`) into the canonical schema.

### Technical Stack

| Component | Library | Purpose |
|---|---|---|
| Async HTTP client | `aiohttp` | Fetching paginated listing pages |
| HTML parsing | `BeautifulSoup` | Extracting JSON-LD and detail fields |
| Headless browser | `Playwright` (Chromium) | Rendering JS-loaded "View More" content |
| Concurrency | `asyncio` | Parallel detail-page workers (10 tabs) |
| Persistence | `openpyxl` | Incremental writes to `opensooq_cars.xlsx` |

### Output Schema

The scraper produces a single Excel workbook (`opensooq_cars.xlsx`) with **25 columns** capturing all relevant vehicle attributes:

> Title, Brand, Model, Trim, Year, Body Type, Condition, Config, Mileage, Price, Currency, Seats, Transmission, Engine Size, Fuel, Exterior Color, Interior Color, Body Condition, Paint, Payment Method, Neighbourhood, City, Description, Link, Image.

### Resilience and Reliability

- **Fault tolerance** — each detail-page fetch is wrapped in try/except so individual failures do not halt the run; failed listings are preserved with partial data.
- **Incremental persistence** — if an output file already exists, new rows are appended rather than overwriting, allowing resumed runs.
- **Timeouts** — HTTP requests use a 15-second timeout; page navigation uses 20 seconds, with a 5-second wait for the "View More" element.
- **Browser realism** — a desktop Chrome User-Agent and `en-US` locale are set on the Playwright context to avoid bot-detection edge cases.

### Result

The scraper successfully collected approximately **15,000 used-car listings** from OpenSooq Jordan, forming the raw dataset for all downstream cleaning, modeling, and visualization work in the Karaj Bi project.


## **Data Description and Understanding**

_[Add data description: field-by-field explanation, dtypes, value ranges, missingness, etc.]_


## **Data Primary Cleaning and Transformation**

The raw scraped dataset (~15K listings from `opensooq_cars.xlsx`) contained noisy, inconsistent, and partially missing data typical of user-submitted classifieds. A multi-stage cleaning and transformation pipeline was developed in Python (pandas) to produce two analysis-ready outputs: one optimized for **BI dashboarding** and one optimized for **machine learning**.

### 1. Initial Sorting and Inspection

The raw dataframe was first sorted by `Brand → Model → Year (desc)` to group comparable vehicles together, and null-value distributions were inspected across all columns to plan an imputation strategy.

### 2. Building a Reliable Price Target

Raw `Price` values were unreliable: many listings carried placeholder zeros, and "Installment" listings represented monthly payment amounts rather than full vehicle prices. To construct a trustworthy target variable (`final_price`):

- **Filter to valid cash listings only** — kept rows where `Price > 0` AND `Payment Method == 'Cash'`.
- **Group-based averaging** — grouped by `[Brand, Model, Year, Trim]` and computed the mean cash price per group.
- **Outlier removal within groups** — computed each listing's price as a ratio of its group median, then excluded ratios outside `[0.3, 3.0]` before recomputing the group average. This protected the mean from being skewed by typos (e.g., a 10,000 JOD car listed at 100,000) or fire-sale prices.
- **Merge back** — every listing inherits its group's clean average price as `final_price`. Rows belonging to groups with no valid cash listings were dropped.

### 3. Engine Size Extraction

The raw `Engine Size` field was a free-text string (e.g., `"2,500 cc"`). A regex (`r'(\d+)\s*cc'`) extracted the numeric component into a clean `engine_size_cc` float column.

### 4. Splitting into Two Datasets

At this point the cleaned dataframe was forked into two purpose-built copies:

| Dataset | Purpose | Filter |
|---|---|---|
| `df_powerbi` | BI dashboard (preserve all rows for richer visualizations) | No drops |
| `df_model` | ML training (require complete specs) | Drop rows missing `Transmission` |

### 5. Dtype Normalization

Scraped values for `Year`, `Mileage`, and `Seats` arrived as strings. All three were coerced to numeric via `pd.to_numeric(..., errors='coerce')` on both datasets.

### 6. Mileage Parsing

Mileage values came in inconsistent formats: `"50,000"`, `"+200000"`, `"1-999"`, etc. A custom `parse_mileage()` function:

- Stripped commas and whitespace.
- Extracted all numeric tokens via regex.
- Returned the **maximum** value, which correctly handles ranges (`"1-999"` → 999), plus-prefixed bounds (`"+200000"` → 200000), and plain numbers.

The result was cast to nullable `Int64` to preserve missing values.

### 7. Year and Mileage Sanity Filters

- Rows with `Year < 1970` were dropped from `df_model` (almost certainly listing errors or hobbyist cars not representative of the active market).
- Mileage outliers were detected using the same group-median ratio method as price (ratio < 0.3 or > 3.0, restricted to groups with ≥3 listings so the median is trustworthy) and dropped from the model dataset.

### 8. Text Standardization

All object-typed columns were normalized:

- Stripped leading/trailing whitespace.
- Restored empty strings and `'nan'` literals back to true `NA` values.
- URL columns (`Link`, `Image`) were skipped since casing is significant.

Categorical fields with semantic meaning (`Brand`, `Model`, `Trim`, `Body Type`, `Condition`, `Transmission`, `Fuel`, `Exterior Color`, `Interior Color`, `Body Condition`, `Paint`, `Payment Method`, `Neighbourhood`, `City`) were converted to **Title Case** to collapse duplicate values caused by inconsistent capitalization (e.g., `"toyota"`, `"TOYOTA"`, `"Toyota"` → `Toyota`).

### 9. Feature Pruning for the Model Dataset

Columns irrelevant to price prediction were dropped from `df_model`:

- `Payment Method` — already used as a filter; constant in the modeling set.
- `Neighbourhood` — too sparse and high-cardinality.
- `Link` — identifier, not a feature.
- `Price` — replaced by the cleaned `final_price` target.

The remaining columns were reordered into a logical structure: identifiers → vehicle specs → condition/appearance → location → target.

### 10. Missing-Value Imputation (Model Dataset)

A **hierarchical group-mode/median strategy** was applied so imputed values stay as close as possible to similar vehicles, falling back to broader groupings only when the narrower group is empty.

**Categorical fields — `Paint`, `Exterior Color`, `Interior Color`:**
Imputed by group **mode** with fallback chain: `[Brand, Model, Year]` → `[Brand, Model]` → `[Brand]` → global mode.

**Mileage:**

- **Rule A:** `Year ≥ 2025` → set Mileage = 0 (assume new).
- **Rule B:** `Condition == 'New'` → set Mileage = 0.
- **Rule C:** Group median by `[Brand, Model, Year]` → `[Brand, Year]` → `[Year]` → global median.
- Result rounded and cast back to `int64`.

**Body Condition:**

- **Rule A:** `Mileage == 0` → `"Excellent With No Defects"` (new cars).
- **Rule B:** Group mode by `[Brand, Model, Year]` → `[Year]` → global mode.

**Trim:**
All remaining nulls filled with `"Base"`, treating "missing trim" as its own semantically meaningful category.

**engine_size_cc:**

- **Rule A:** `Fuel == 'Electric'` → 0 (no combustion engine).
- **Rule B:** Group median by `[Brand, Model, Year]` → `[Brand, Model]` → `[Brand, Body Type]` → `[Body Type]` → global median. Body Type is a strong fallback because SUVs, sedans, and trucks have characteristic engine-size ranges.

### 11. Final Schema Normalization

All column names in `df_model` were converted to `snake_case` (lowercased, spaces → underscores) for downstream compatibility with Python ML libraries and KNIME.

### 12. Export

Two final files were produced:

| File | Format | Consumer | Reason |
|---|---|---|---|
| `cars_powerbi.xlsx` | Excel (UTF-8) | Power BI dashboard | Preserves Arabic text reliably; easy native import |
| `cars_model.csv` | CSV (`utf-8-sig`) | Python (LightGBM) + KNIME (H2O GBM) | Lighter, faster reload, BOM ensures Excel/KNIME read encoding correctly |

### Summary of Decisions

| Concern | Decision | Rationale |
|---|---|---|
| Unreliable raw price | Replace with cleaned group-average `final_price` | Filters out installment listings and within-group outliers |
| Mixed mileage formats | Regex-extract max numeric token | Handles ranges, prefixes, and plain numbers uniformly |
| Sparse categorical fields | Hierarchical group-mode imputation | Stays close to similar vehicles before falling back globally |
| Missing engine size | Fuel-aware + group-median imputation | Electrics correctly set to 0; ICE cars get peer-group values |
| Two output files | Split BI vs. ML datasets | Each consumer has different completeness requirements |


## **Data Visualization and Insights**

_[Add exploratory visualizations and key insights derived from the cleaned data — distributions, correlations, segment comparisons, etc.]_


## **Dashboard Design & Business Insights**

A six-page **Power BI** dashboard was built on top of the `cars_powerbi.xlsx` dataset to turn the cleaned listings into actionable market intelligence. Each page targets a distinct analytical lens, so that a user can move from a high-level market view down to specific brand, condition, or location-driven insights.

### Page 1 — Market Overview

A top-level snapshot of the Jordanian used-car market. Surfaces headline KPIs (total listings, average price, average mileage, average year) along with overall distributions of body types, fuel types, and transmission. Serves as the entry point and orients the user before drilling deeper.

### Page 2 — Price Intelligence

Focuses on the price dimension. Visualizes the overall price distribution, identifies the most and least expensive segments, and breaks down average price by key factors such as year, fuel, and body type. Highlights price ranges that dominate the market versus premium niches.

### Page 3 — Brand & Model Analysis

Compares performance across brands and their underlying models. Shows market share by brand, the most-listed models, and average price per brand/model. Useful for spotting which brands dominate supply and which models hold their value best in the listed inventory.

### Page 4 — Condition & Mileage Impact

Examines how vehicle condition and mileage drive price. Visualizes price-vs-mileage trends, average price by condition category, and the interaction between body condition, paint, and asking price. Quantifies the depreciation effect of accumulated kilometers on listed prices.

### Page 5 — City & Regional Trends

Adds the geographic dimension. Breaks down listings, average price, and brand mix across Jordanian cities, revealing regional supply patterns (e.g., which cities skew toward higher-end inventory and which serve the budget segment).

### Page 6 — Market Trends

Looks at temporal and structural trends across the dataset — distribution of model years, age-vs-price curves, and how newer model years are priced relative to older inventory. Helps identify which model-year segments are most active in the market.

### Design Approach

- **Consistent visual language** across all six pages (shared color palette, slicer style, and KPI layout) so users can move between pages without re-orienting.
- **Slicer-driven interactivity** — Brand, Year, City, and Fuel filters propagate across visuals on each page, enabling ad-hoc exploration without page redesign.
- **Progressive disclosure** — pages are ordered from broad (Market Overview) to specific (City, Trends), supporting both quick scanning and deeper analysis in a single dashboard.


## **Advanced Analytics and AI Modeling**

### Objective

Train a regression model to predict the `final_price` of a used car given its specifications (brand, model, trim, year, mileage, engine size, fuel, condition, body condition, paint, colors, body type, city), then expose the trained model for downstream inference in the Karaj Bi application.

### Model Choice: LightGBM Regressor

**LightGBM** (Gradient Boosting Decision Trees) was selected as the primary model for the following reasons:

- **Native categorical handling** — used-car data is dominated by high-cardinality categorical features (Brand, Model, Trim, City, colors). LightGBM splits on category values directly, avoiding the dimensionality explosion of one-hot encoding.
- **Non-linear relationships** — captures complex interactions between brand, year, mileage, and trim that drive price.
- **Robust to skewed targets** — tree-based models do not assume normality, which suits Jordan's heavy-tailed used-car price distribution.
- **Speed and scale** — efficient on a ~15K-row tabular dataset; allows fast iteration during tuning.
- **Built-in regularization** — `min_child_samples`, `feature_fraction`, and `bagging_fraction` control overfitting without heavy preprocessing.
- **Feature importance** — produces interpretable gain/split importances, valuable for explaining model behavior in a BI context.

### Data Preparation for Modeling

The cleaned modeling dataset (`cars_model.csv`) was loaded into pandas. Features and target were separated:

- **Target:** `final_price` (cleaned group-average cash price computed during the cleaning stage).
- **Features:** all remaining columns — `brand`, `model`, `trim`, `year`, `body_type`, `mileage`, `engine_size_cc`, `fuel`, `condition`, `body_condition`, `paint`, `exterior_color`, `interior_color`, `city`.

All object/string columns were cast to pandas `category` dtype so LightGBM could handle them natively without manual encoding.

### Train / Test Split

A standard 80/20 holdout split was used with a fixed `random_state=42` for reproducibility:

| Split | Share | Purpose |
|---|---|---|
| Train | 80% | Model fitting |
| Test  | 20% | Held-out evaluation and early-stopping signal |

### Model Configuration

The `LGBMRegressor` was instantiated with parameters tuned for moderate-sized tabular data with high categorical cardinality:

| Hyperparameter | Value | Rationale |
|---|---|---|
| `n_estimators` | 2000 | Upper bound; early stopping selects the optimal round |
| `learning_rate` | 0.05 | Conservative rate; combined with many estimators for smoother learning |
| `num_leaves` | 63 | Allows enough complexity to capture brand×model×year interactions |
| `min_child_samples` | 20 | Prevents splits on tiny leaves (overfitting on rare car groups) |
| `feature_fraction` | 0.9 | Column subsampling per tree — light regularization |
| `bagging_fraction` | 0.9 | Row subsampling — reduces variance |
| `bagging_freq` | 5 | Refresh bagging every 5 iterations |
| `random_state` | 42 | Reproducibility |

### Training with Early Stopping

The model was trained with the test set as a validation signal and **early stopping after 100 rounds without MAE improvement**, ensuring the optimal number of boosting rounds was chosen automatically rather than fixed:

```python
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    eval_metric="mae",
    categorical_feature=cat_cols,
    callbacks=[lgb.early_stopping(100), lgb.log_evaluation(100)],
)
```

Progress was logged every 100 iterations to monitor convergence.

### Evaluation Metrics

Multiple complementary metrics were computed to give a complete view of model performance:

| Metric | Value | Interpretation |
|---|---|---|
| **MAE** | ~1,935 JOD | Average absolute error per prediction |
| **RMSE** | — | Penalizes large errors more heavily |
| **R²** | 0.817 | ~82% of price variance explained |
| **MAPE** | — | Mean absolute percentage error |
| **Accuracy ±10%** | — | Share of predictions within ±10% of true price |
| **Accuracy ±20%** | — | Share of predictions within ±20% of true price |

The **±10% / ±20% tolerance accuracy** is a business-friendly metric: it answers the question *"how often does the model land in the right ballpark?"* — more intuitive for end users than RMSE alone.

### Feature Importance

LightGBM's built-in `feature_importances_` was extracted and ranked. The dominant predictors aligned with domain expectations — **year**, **mileage**, **brand**, **model**, and **engine size** consistently emerged as the strongest signals, confirming that the model learned economically sensible pricing logic rather than spurious patterns.

### Model Persistence

The trained model and inference-time metadata were serialized with `joblib`:

**`lgbm_car_price.pkl`** — the fitted LightGBM regressor.

**`feature_options.pkl`** — a companion artifact containing the metadata the front-end and inference layer need to construct valid input rows:

- `categorical` — list of unique values per categorical column (drives dropdown menus).
- `feature_order` — the exact column order the model expects at inference time.
- `cat_cols` — which columns must be cast to `category` dtype before prediction.
- `brand_model_trim` — nested mapping `{Brand: {Model: [Trims]}}` so the UI can cascade trim options based on the selected brand and model.
- `brand_model_body` — nested mapping `{Brand: {Model: [Body Types]}}` for the same cascading behavior on body type.

This design separates the **model artifact** from the **UI-driving schema**, allowing the front-end to render context-aware dropdowns without needing access to the original training dataframe.

### Summary

| Decision | Rationale |
|---|---|
| LightGBM over linear models | Handles categorical features natively, captures non-linear interactions |
| Native `category` dtype (no one-hot) | Preserves cardinality and trains faster |
| 80/20 split with early stopping | Prevents overfitting; auto-selects optimal boosting rounds |
| Multi-metric evaluation (MAE/R²/MAPE/tolerance) | Combines statistical and business-readable accuracy |
| Joblib + feature-options bundle | Decouples model from UI schema; enables cascading dropdowns at inference time |


## **Tools Research and Selection Effort**

_[Add tool-selection rationale: Python, pandas, LightGBM, KNIME (H2O GBM), Power BI, Streamlit, Playwright, etc.]_


## **Project Deployment Effort – Use Case**

The trained model was deployed as a lightweight **Streamlit** web application, providing a simple interactive interface for end users to estimate used-car prices in Jordan.

### Application Flow

1. **Load artifacts** — the saved LightGBM model (`lgbm_car_price.pkl`) and the feature-options bundle (`feature_options.pkl`) are loaded once at startup.
2. **Render input form** — a two-column layout collects all 14 model features. Dropdowns are populated directly from the feature-options metadata.
3. **Cascading selectors** — the **Model** dropdown is filtered by the chosen **Brand**, and **Trim** and **Body Type** are filtered by the chosen Brand + Model, using the nested `brand_model_trim` and `brand_model_body` dictionaries. This guarantees only valid combinations are selectable.
4. **Build inference row** — on submit, a single-row dataframe is constructed in the exact `feature_order` expected by the model, and categorical columns are cast to `pd.Categorical` using the **same category levels** seen during training (critical to avoid LightGBM treating unseen levels as nulls).
5. **Predict and present** — the model returns a point estimate; the UI also displays an expected range computed as `[prediction − MAE, prediction]`, where MAE ≈ 1,800 JOD reflects the typical model error from evaluation.

### Why Streamlit

- Zero front-end code — pure Python.
- Native widgets for categorical dropdowns and numeric inputs.
- Trivial to share locally or deploy as a hosted demo.
- Aligned with the academic/PoC nature of the project.

### Output

The user receives:

- **Estimated price** — the model's point prediction in JOD.
- **Expected range** — a confidence-band interpretation based on the model's typical error, giving a more honest read on uncertainty than a single number.


## **Results**

_[Add final results summary: model performance numbers, dashboard takeaways, business value delivered.]_


## **References**

_[Add references: OpenSooq, LightGBM paper, pandas, scikit-learn, Power BI documentation, etc.]_