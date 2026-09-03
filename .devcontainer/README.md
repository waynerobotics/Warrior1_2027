


This docker setup is designed to allow anyone to use this environment for development. The Dockerfile consists of ROS2 Humble, as well as 
many basic tools like Gazebo and Rviz2. Docker compose is used to launch the environment, taking the config from docker-compose.yml and using the entrypoint.sh as a means to launch the setup script.

For execution, enter the following commands:

(In .devcontainer)

xhost +local:docker # Gives docker access to use ports for GUI on your home machine from the container

docker compose build --no-cache # Builds the docker image from the Dockerfile, and docker-compose.yml

docker compose up -d --force-recreate # Runs the container in the background (-d) so the terminal can be used for other things

