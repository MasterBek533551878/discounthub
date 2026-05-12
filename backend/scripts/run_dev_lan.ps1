# Run DiscountHub backend so other devices on the same Wi-Fi can access it.
# Example phone URL: http://192.168.1.6:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
