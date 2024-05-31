# isolated-llm

Three dockerized services:
* api-server (started)
* ocr-service
* llama3-model

## ocr-service

sudo apt update
sudo apt install tesseract-ocr
sudo apt install libtesseract-dev


  # llama3-model:
  #   build: ./llama3-model
  #   networks:
  #     - internal