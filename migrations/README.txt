For running migrations

Step one:
Ensure the virtual environment is activated by running in the command line:
>> .\.venv\Scripts\activate


Step two:
Verify that the flask works by running the following command:
>> flask --version
>> flask routes

Step three:
If the environment is not working, then run the following command:
>> $env:FLASK_APP = "main:app"
>> $env:FLASK_ENV = "development"

Step four:
Run the migrations by running the following command:
>> flask db upgrade
