import pandas as pd
from typing import Any, Dict, List, Text
import logging
import json

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from rapidfuzz import process, fuzz
import ast

from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "RAW_recipes.csv"

try:
    df_recipes = pd.read_csv(DATA_PATH)
    logger.info(f"Loaded {len(df_recipes)} recipes from {DATA_PATH}")
except FileNotFoundError:
    logger.error(f"Recipe database not found at {DATA_PATH}")
    raise RuntimeError(f"Recipe database not found at {DATA_PATH}")  

def parse(val):
    """Parse recipe ingredients/steps from CSV. Safely handles list literals from trusted CSV data."""
    try:
        return [i.strip().lower() for i in ast.literal_eval(val)]
    except Exception:
        return [i.strip().lower() for i in str(val).split(",")]

# Precalculer les ingredients et les instructions pour passer d'une chaine de caracteres "[ingredients]" à une liste [ingredients]
df_recipes["ingredients_list"] = df_recipes["ingredients"].apply(parse)
df_recipes["ingredients_text"] = df_recipes["ingredients_list"].apply(lambda x: " ".join(x))
df_recipes["steps_list"] = df_recipes["steps"].apply(parse)

# Global variables to store recipe information across actions
closest_match = None  # Cache recipe fuzzy match result to avoid duplicate searches

from typing import List, Dict

def parse_restrictions(restrictions_str: str) -> List[str]:
    """
    Parse restrictions from user input, handling various formats:
    - "halal" → ["halal"]
    - "halal, vegetarian" → ["halal", "vegetarian"]
    - "halal and vegetarian" → ["halal", "vegetarian"]
    - "halal, vegetarian and pescatarian" → ["halal", "vegetarian", "pescatarian"]
    """
    if not restrictions_str:
        return []
    
    # Replace "and" with comma for consistent splitting
    text = restrictions_str.replace(" and ", ",")
    
    # Split by comma and clean up
    restrictions_list = [r.strip().lower() for r in text.split(",") if r.strip()]
    
    return restrictions_list


def recipe_matches_restrictions(recipe_row, restrictions: str) -> bool:
    # Gestion des cas vides
    if not restrictions or str(restrictions).lower() == "no":
        return True

    # Parse restrictions handling "and" separators and commas
    restrictions_list = parse_restrictions(str(restrictions))
    

    # Extraction des ingrédients
    ingredients_list = recipe_row["ingredients_list"]

    forbidden_map = {
        "vegetarian": ["chicken", "beef", "pork", "bacon", "steak", "lamb", "duck", "turkey", "fish", "shrimp", "gelatin"],
        "vegan": ["milk", "cheese", "egg", "butter", "honey", "cream", "yogurt", "whey", "chicken", "beef", "pork", "fish", "lard"],
        "halal": ["pork", "bacon", "ham", "lard", "gelatin", "alcohol", "wine", "beer"],
        "gluten-free": ["flour", "wheat", "barley", "rye", "bread", "pasta", "couscous", "semolina", "malt"],
        "dairy-free": ["milk", "cheese", "butter", "cream", "yogurt", "whey", "casein", "lactose"],
        "pescatarian": ["chicken", "beef", "pork", "bacon", "steak", "lamb", "duck", "turkey"],
        "nut-free": ["peanut", "almond", "walnut", "cashew", "pecan", "hazelnut", "pistachio"],
        "lactose-intolerant": ["milk", "cheese", "butter", "cream", "yogurt", "whey", "curds", "lactose", "casein", "malted milk"],
        "kosher": ["pork", "bacon", "ham", "lard", "rabbit", "gelatin", "shrimp", "crab", "lobster"]
    }

    # Thresholds pour le fuzzy matching
    restriction_match_threshold = 75  # Seuil pour matcher les restrictions (ex: "vegan" vs "végan")
    ingredient_match_threshold = 70   # Seuil pour matcher les ingrédients (ex: "cheese" vs "cheddar cheese")

    # PHASE A : Vérification des ingrédients interdits avec fuzzy matching
    for user_restriction in restrictions_list:
        # Fuzzy match la restriction pour gérer les variations d'écriture
        matched_restriction = process.extractOne(user_restriction, forbidden_map.keys())
        
        if matched_restriction and matched_restriction[1] >= restriction_match_threshold:
            restriction_key = matched_restriction[0]
            forbidden_list = forbidden_map[restriction_key]
            
            # Pour chaque ingrédient interdit, vérifier s'il existe dans la recette avec fuzzy matching
            for forbidden_ingredient in forbidden_list:
                for recipe_ingredient in ingredients_list:
                    # Utiliser partial_ratio pour détecter les correspondances partielles
                    # (ex: "cheese" trouvé dans "cheddar cheese", "milk" trouvé dans "whole milk")
                    similarity = fuzz.partial_ratio(forbidden_ingredient.lower(), recipe_ingredient.lower())
                    if similarity >= ingredient_match_threshold:
                        return False

    return True


class ActionGetIngredients(Action):
    def name(self) -> Text:
        return "action_get_ingredients"

    def run(self, dispatcher, tracker, domain):
        global closest_match
        recipe_name = tracker.get_slot("recipe")
        
        # Check if user selected a recipe by number from suggestions
        if recipe_name and recipe_name.strip().isdigit():
            suggested_recipes_json = tracker.get_slot("suggested_recipes")
            if suggested_recipes_json:
                try:
                    suggested_recipes = json.loads(suggested_recipes_json)
                    recipe_index = int(recipe_name.strip()) - 1  # Convert 1-based to 0-based
                    if 0 <= recipe_index < len(suggested_recipes):
                        recipe_name = suggested_recipes[recipe_index]
                        logger.debug(f"User selected recipe #{recipe_name.strip()}: {recipe_name}")
                    else:
                        dispatcher.utter_message(f"Invalid selection. Please choose between 1 and {len(suggested_recipes)}.")
                        return [SlotSet("recipe_valid", False)]
                except (json.JSONDecodeError, ValueError):
                    logger.error("Failed to parse suggested recipes")
                    pass
        
        # Fuzzy matching - perform search only once and cache result
        all_recipe_names = df_recipes["name"].tolist()
        closest_match = process.extractOne(recipe_name, all_recipe_names)
        logger.debug(f"Recipe search: {recipe_name} -> {closest_match}")
        if closest_match:
            recipe_name = closest_match[0]  # Use fuzzy match to handle typos

        # On récupère le DataFrame des correspondances
        matching_df = df_recipes[df_recipes["name"].str.lower() == recipe_name.lower()]

        if matching_df.empty:
            msg = f"Sorry, I couldn't find the recipe '{recipe_name}'. Try another recipe or search by ingredients."
            dispatcher.utter_message(msg)
            logger.warning(f"Recipe not found: {recipe_name}")
            return [SlotSet("recipe_valid", False)]
        
        # On extrait la PREMIÈRE ligne en tant que Series
        recipe_series = matching_df.iloc[0]
        
        restrictions = tracker.get_slot("dietary_restrictions") or "no"

        # On passe la Series à la fonction de vérification
        if not recipe_matches_restrictions(recipe_series, restrictions):
            dispatcher.utter_message(
                f"The recipe '{recipe_name}' does not respect your dietary restrictions : {restrictions}."
            )
            return [SlotSet("recipe_valid", False)]

        # Recipe passed validation - extract and display ingredients
        ingredients_list = recipe_series["ingredients_list"]
        formatted_ingredients = "\n".join([f"- {ing}" for ing in ingredients_list])
        
        dispatcher.utter_message(
            text=f"Here are the ingredients for {recipe_name}:\n{formatted_ingredients}"
        )
        logger.info(f"Recipe '{recipe_name}' validated and ingredients shown")
        return [SlotSet("recipe_valid", True)]


class ActionGetInstructions(Action):
    def name(self) -> Text:
        return "action_get_instructions"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        global closest_match
        recipe_name = tracker.get_slot("recipe")
        # Use the pre-calculated closest match from ActionGetIngredients
        if closest_match:
            recipe_name = closest_match[0]

        recipe_row = df_recipes[df_recipes["name"].str.lower() == recipe_name.lower()]

        if recipe_row.empty:
            msg = f"Sorry, I couldn't find the recipe '{recipe_name}'."
            dispatcher.utter_message(msg)
            logger.error(f"Recipe not found during instructions: {recipe_name}")
            return [SlotSet("recipe_valid", False)]

        # IMPORTANT: Re-validate dietary restrictions before showing instructions
        # This ensures consistency - if recipe was rejected for ingredients, it's also rejected here
        recipe_series = recipe_row.iloc[0]
        restrictions = tracker.get_slot("dietary_restrictions") or "no"
        
        if not recipe_matches_restrictions(recipe_series, restrictions):
            msg = f"The recipe '{recipe_name}' does not respect your dietary restrictions: {restrictions}."
            dispatcher.utter_message(msg)
            logger.warning(f"Recipe '{recipe_name}' rejected due to dietary restrictions")
            return [SlotSet("recipe_valid", False)]

        # Extract and format cooking instructions
        steps_list = recipe_series["steps_list"]
        formatted_instructions = "\n".join([f"{i}. {step}" for i, step in enumerate(steps_list, 1)])
        
        dispatcher.utter_message(text=f"Follow these steps for {recipe_name}:\n{formatted_instructions}")
        logger.info(f"Instructions shown for {recipe_name}")
        return [SlotSet("recipe_valid", True)]


class ActionUtterRecipeComplete(Action):
    def name(self) -> Text:
        return "action_utter_recipe_complete"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        global closest_match
        # Use the validated recipe name and set it in slot for response template
        recipe_name = "your recipe"
        if closest_match:
            recipe_name = closest_match[0]
        
        dispatcher.utter_message(f"Enjoy cooking {recipe_name}!")
        logger.info(f"Recipe completion message shown for {recipe_name}")
        return [SlotSet("recipe", recipe_name)]


class ActionSuggestRecipes(Action):
    def name(self) -> Text:
        return "action_suggest_recipes"

    def run(self, dispatcher, tracker, domain) -> List[Dict[Text, Any]]:
        global closest_match
        closest_match = None  # Reset when suggesting recipes (will be set when user picks one)

        restrictions = tracker.get_slot("dietary_restrictions") or "no"

        user_text = tracker.get_slot("ingredients")
        if not user_text:
            dispatcher.utter_message("Please tell me the ingredients you have.")
            return []

        user_ingredients = [i.strip().lower() for i in user_text.split(",")]

        user_set = set(user_ingredients)

        threshold = 60  # Seuil pour le score minimale acceptable (pour selectionner le recipe ayant le plus d'ingredients en commun avec ce que l'utilisateur dispose déja)

        matched_recipes = []
        for _, row in df_recipes.iterrows():

            # On élimine les recipes contenant des ingredients interdites pour l'utilisateur (s'il a des restrictions alimentaires)
            if not recipe_matches_restrictions(row, restrictions):
                continue

            recipe_ingredients = row["ingredients_list"]
            recipe_text = row["ingredients_text"]

            if not recipe_ingredients:
                continue

            # 3 scorers utiles en "texte vs texte"
            score_token_set = fuzz.token_set_ratio(user_text, recipe_text)
            score_partial = fuzz.partial_ratio(user_text, recipe_text)
            score = max(score_token_set, score_partial)

            if score >= threshold:
                missing = set(recipe_ingredients) - user_set # compter les ingredients manquants
                matched_recipes.append(
                    (row["name"], score, len(missing))
                )


        if not matched_recipes:
            msg = "Sorry, I couldn't find any recipes with those ingredients. Try different ingredients or adjust your dietary restrictions."
            dispatcher.utter_message(msg)
            logger.info(f"No recipes found for ingredients: {user_text}")
            return []

        # Sort by matching score (highest first) and take top 5
        matched_recipes.sort(key=lambda x: x[1], reverse=True)
        top = matched_recipes[:5]
        
        # Extract just the recipe names for storing in slot
        recipe_names = [name for name, score, missing_count in top]
        suggested_recipes_json = json.dumps(recipe_names)
        
        msg = "Here are some recipes you can make with your ingredients:\n"
        for i, (name, score, missing_count) in enumerate(top, 1):
            msg += f"{i}. {name} ({missing_count} ingredient(s) missing)\n"
        msg += "\nType the number (1-5) of the recipe you want to cook."
        
        dispatcher.utter_message(msg)
        logger.info(f"Found {len(top)} matching recipes for ingredients")
        return [SlotSet("suggested_recipes", suggested_recipes_json)]