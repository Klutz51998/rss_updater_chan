# rss\_updater\_chan



**Command to build a new docker image:**



**docker build -t rss-updater .**



**Command to run the docker image:**



**docker run -d --name rss-updater-container rss-updater**



**Checking Output**



To check the logs/output of the script, just run this command and it will print which feeds has been updated, or when the next scheduled update will run **after running said command:**



**docker logs rss-updater-container**

