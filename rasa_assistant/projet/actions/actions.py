import pandas as pd
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from pathlib import Path 
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "RAW_recipes.csv"
df_recipes = pd.read_csv(DATA_PATH)  


class ActionGetIngredients(Action):
    def name(self) -> Text:
        return "action_get_ingredients"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        recipe_name = tracker.get_slot("recipe")

        # Chercher la recette dans le CSV
        recipe_row = df_recipes[df_recipes["name"].str.lower() == recipe_name.lower()]

        if recipe_row.empty:
            dispatcher.utter_message(f"Sorry, I couldn't find the recipe '{recipe_name}'.")
            return []

        # Récupérer les ingrédients
        ingredients_str = recipe_row.iloc[0]["ingredients"] 
        ingredients_list = [i.strip() for i in ingredients_str.split(",")]

        dispatcher.utter_message(f"Here are the ingredients for {recipe_name}: {', '.join(ingredients_list)}")
        return []


class ActionGetInstructions(Action):
    def name(self) -> Text:
        return "action_get_instructions"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        recipe_name = tracker.get_slot("recipe")

        recipe_row = df_recipes[df_recipes["name"].str.lower() == recipe_name.lower()]

        if recipe_row.empty:
            dispatcher.utter_message(f"Sorry, I couldn't find the recipe '{recipe_name}'.")
            return []

        instructions = recipe_row.iloc[0]["steps"]
        dispatcher.utter_message(f"Follow these steps for {recipe_name}:\n{instructions}")
        return []


class ActionUtterRecipeComplete(Action):
    def name(self) -> Text:
        return "action_utter_recipe_complete"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message("Your recipe is complete! Enjoy your cooking! ")
class ActionSuggestRecipes(Action):
    def name(self) -> Text:
        return "action_suggest_recipes"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        # récupérer le slot ingredients (déjà une liste)
        user_ingredients = tracker.get_slot("ingredients")
        if not user_ingredients:
            dispatcher.utter_message("Please tell me the ingredients you have.")
            return []

        # nettoyer et mettre en minuscules
        user_ingredients = [i.strip().lower() for i in user_ingredients]

        # chercher les recettes correspondantes
        matched_recipes = []
        for idx, row in df_recipes.iterrows():
            recipe_ingredients = [i.strip().lower() for i in row["ingredients"].split(",")]
            common = set(user_ingredients) & set(recipe_ingredients)
            if common:
                matched_recipes.append((row["name"], len(common)))

        if not matched_recipes:
            dispatcher.utter_message("Sorry, I couldn't find any recipes with those ingredients.")
            return []

        # trier par nombre d'ingrédients communs
        matched_recipes.sort(key=lambda x: x[1], reverse=True)
        top_recipes = [r[0] for r in matched_recipes[:5]]

        # envoyer le message
        msg = "Here are some recipes you can make with your ingredients:\n"
        for i, r in enumerate(top_recipes, 1):
            msg += f"{i}. {r}\n"
        msg += "Which one would you like to prepare?"
        dispatcher.utter_message(msg)

        return []
