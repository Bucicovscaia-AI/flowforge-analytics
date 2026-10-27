# Sample data

All datasets in this folder are **fabricated (synthetic) demonstration data**,
generated for development and testing. They do not describe any real business,
customer or transaction, and results produced from them are not genuine
business findings.

| File | Rows | Contents |
| --- | --- | --- |
| `retail_sales_2026_synthetic.csv` | 1,152 | All nine columns, January to June 2026, with deliberate problems: 15 duplicate rows, blank and `N/A` values, invalid dates, negative quantities, missing prices, prices with a `£` sign, inconsistent region capitalisation and padded product names |
| `web_orders_minimal_synthetic.csv` | 518 | Only the four required columns, to show KPIs that are reported as not available |

Both files are produced by `generate_sample_data.py` with a fixed seed, so
running it again gives identical files:

```bash
python sample-data/generate_sample_data.py
```
