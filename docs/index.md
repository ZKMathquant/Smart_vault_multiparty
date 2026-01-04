```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 demo.py
python3 web_interface/app.py
python3 -m unittest discover tests/ -v
