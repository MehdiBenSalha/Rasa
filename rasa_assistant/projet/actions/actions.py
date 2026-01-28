import pandas as pd
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


# Charger le CSV une seule fois pour toutes les actions
df_recipes = pd.read_csv("Food Ingredients and Recipe Dataset with Image Name Mapping.csv")  


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
        return "utter_recipe_complete"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message("Your recipe is complete! Enjoy your cooking! ")
