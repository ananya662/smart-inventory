# Smart Inventory & Sales Decision Engine (backend)
```
pip install -r requirements.txt
python generate_data.py      # sample_sales.csv + ground_truth.json
python evaluate.py           # accuracy vs planted ground truth
uvicorn main:app --reload    # docs at http://localhost:8000/docs
```
CSV columns: date, product_id, product_name, units_sold, price, stock_on_hand (category optional).
