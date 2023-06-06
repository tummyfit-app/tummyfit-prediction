import numpy as np
import pandas as pd
import tensorflow as tf
import os
from flask import Flask, jsonify ,request


app  = Flask(__name__)
# Update the model and weight file paths
model_path = os.path.join('model', 'tummyfit_model.json')
weights_path = os.path.join('model', 'tummyfit_model_weights.h5')

with open(model_path, 'r') as file:
    model_json = file.read()
model = tf.keras.models.model_from_json(model_json)
model.load_weights(weights_path)



# Preprocess input data
def preprocess_input(calorie_requirement, halal, vegetarian, vegan, gluten_free, dairy_free):
    # Normalize calorie_requirement to range [0, 1]
    calorie_requirement /= 3000.0

    input_data = [calorie_requirement, halal, vegetarian, vegan, gluten_free, dairy_free]
    return np.array(input_data)

# Generate menu based on user input
def generate_menu(model, input_data, data):
 
    input_data = np.array([input_data])
    predicted_probabilities = model.predict(input_data)[0]
    menu_indices = np.argmax(predicted_probabilities)
    
    menu_combination = []
    categories = ['Breakfast', 'Lunch', 'Dinner', 'Snack 1', 'Snack 2']
    for index, category in enumerate(categories):
        category_menu = food_data[food_data[category] == 1]
  
        # Filter menu based on calorie requirement and preferences
        filtered_menu = category_menu[
            (category_menu['Calories'] <= (data[0] - sum(menu['Calories'] for menu in menu_combination))) &
            (category_menu['Halal'] == bool(data[1])) &
            (category_menu['Vegetarian'] == bool(data[2])) &
            (category_menu['Vegan'] == bool(data[3])) &
            (category_menu['Gluten Free'] == bool(data[4])) &
            (category_menu['Dairy Free'] == bool(data[5]))
        ]

        if len(filtered_menu) > 0:
            menu_index = np.random.choice(len(filtered_menu))
            menu_combination.append(filtered_menu.iloc[menu_index])
        else:
            # If no menu available within the remaining calorie limit and preferences, regenerate the combination
            return generate_menu(model, input_data, data)

    return menu_combination

# Generate weekly meal plan
def generate_weekly_menu(model, input_data ,data):
    weekly_menu = []
    for _ in range(7):
        menu_combination = generate_menu(model, input_data, data)
        weekly_menu.append(menu_combination)
    return weekly_menu


# Calculate daily calorie requirement
def calculate_daily_calorie_requirement(weight, height, sex, age, daily_activity, goal):
    # Menghitung BMR (Basal Metabolic Rate)
    if sex == "male":
        bmr = 66 + (13.75 * weight) + (5 * height) - (6.75 * age)
    elif sex == "female":
        bmr = 655 + (9.56 * weight) + (1.85 * height) - (4.68 * age)
    else:
        raise ValueError("Invalid sex. Please enter 'male' or 'female'.")

    # Menyesuaikan kebutuhan kalori berdasarkan aktivitas harian
    activity_factors = {
        "sedentary": 1.2,
        "lightly active": 1.375,
        "moderately active": 1.55,
        "very active": 1.725,
        "extra active": 1.9
    }
    if daily_activity not in activity_factors:
        raise ValueError("Invalid daily activity. Please choose from: 'sedentary', 'lightly active', 'moderately active', 'very active', 'extra active'.")
    
    daily_calorie_requirement = bmr * activity_factors[daily_activity]

    # Menyesuaikan kebutuhan kalori berdasarkan tujuan
    if goal == "Maintain weight":
        return daily_calorie_requirement
    elif goal == "Weight loss":
        # Mengurangi 500 kalori per hari untuk tujuan penurunan berat badan
        calorie_deficit = 500
        return daily_calorie_requirement - calorie_deficit
    else:
        raise ValueError("Invalid goal. Please choose from: 'Maintain weight' or 'Weight loss'.")


# Read food data
food_data_path =os.path.join('food_data', 'data-tummyfit-v4.csv')
food_data = pd.read_csv(food_data_path)

# Food categories
categories = ['Breakfast', 'Lunch', 'Dinner', 'Snack 1', 'Snack 2']



@app.route("/" , methods=["POST"])
def home(): 
  
   payload = request.json

   cal_need = calculate_daily_calorie_requirement(payload["weight"], payload["height"], payload["sex"], payload["age"], payload["daily_activity"], payload["goal"])
   process_data = preprocess_input(cal_need,payload["halal"], payload["vegetarian"] , payload["vegan"], payload["gluten_free"], payload["dairy_free"])

   weekly_menu = generate_weekly_menu(model, process_data , [cal_need, payload["halal"], payload["vegetarian"], payload["vegan"], payload["gluten_free"], payload["dairy_free"]])
   days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
   output = []
   for day, menu_combination in zip(days, weekly_menu):
     menu_info = {"Day": day, "Menu": []}
     total_calories = sum(menu['Calories'] for menu in menu_combination)
    
     for index, category in enumerate(categories):
        menu = menu_combination[index]
        recipe_title = menu['Recipe Title']
        calories = menu['Calories']
        halal = "Yes" if menu['Halal'] == 1 else "No"
        vegetarian = "Yes" if menu['Vegetarian'] == 1 else "No"
        vegan = "Yes" if menu['Vegan'] == 1 else "No"
        gluten_free = "Yes" if menu['Gluten Free'] == 1 else "No"
        dairy_free = "Yes" if menu['Dairy Free'] == 1 else "No"
        ingredients = menu['Ingredients']
        instructions = menu['Instructions']
        

        menu_info["Menu"].append({
            "Category": category,
            "Recipe Title": recipe_title,
            "Calories": calories,
            "Halal": halal,
            "Vegetarian": vegetarian,
            "Vegan": vegan,
            "Gluten Free": gluten_free,
            "Dairy Free": dairy_free,
            "Ingredients": ingredients,
            "Instructions": instructions
        }) 

     menu_info["Total Calories"] = int(total_calories)
     menu_info["Requirement_Calorie"]= int(cal_need)
     output.append(menu_info)

   
   return output


if __name__ == '__main__' : 
    app.run(host="0.0.0.0" , port=8000)
