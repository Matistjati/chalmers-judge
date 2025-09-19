import django
from django.contrib.staticfiles import finders

print(finders.find('your_static_file.css'))

