


git init 
uv venv --python 3.12
.\.venv\Scripts\activate.ps1
uv pip install -r .\requirements.txt

 + annotated-types==0.8.0
 + black==26.5.1
 + click==8.4.2
 + colorama==0.4.6
 + colorlog==6.12.0
 + iniconfig==2.3.0
 + mypy-extensions==1.1.0
 + packaging==26.2
 + pathspec==1.1.1
 + platformdirs==4.11.0
 + pluggy==1.6.0
 + pydantic==2.13.4
 + pydantic-core==2.46.4
 + pygments==2.20.0
 + pytest==9.1.1
 + python-dotenv==1.2.2
 + pytokens==0.4.1
 + pyyaml==6.0.3
 + ruff==0.16.1
 + typing-extensions==4.16.0
 + typing-inspection==0.4.2


$env:PYTHONPATH="."
python .\tests\test_config.py


pytest tests/test_config.py
python -m tests.test_config


 + anyio==4.14.2
 + certifi==2026.7.22
 + h11==0.16.0
 + httpcore==1.0.9
 + httpx==0.28.1
 + idna==3.18