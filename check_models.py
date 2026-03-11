import google.generativeai as genai

genai.configure(api_key="AIzaSyCx4Kg2dMuVI8m3-DBGKGZyMI5s-mP-j5A")

for model in genai.list_models():
    print(model.name)