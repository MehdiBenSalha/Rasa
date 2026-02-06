import pandas as pd
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from rapidfuzz import process, fuzz
import ast

from pathlib import Path 
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "RAW_recipes.csv"
df_recipes = pd.read_csv(DATA_PATH)  


from typing import List, Dict

def recipe_matches_restrictions(recipe_row, restrictions: str) -> bool:
    # Gestion des cas vides
    if not restrictions or str(restrictions).lower() == "no":
        return True

    if isinstance(restrictions, str):
        restrictions_list = [r.strip().lower() for r in restrictions.split(",")]
    else:
        restrictions_list = restrictions

    # Extraction sécurisée des ingrédients
    # .get() sur une Series évite l'ambiguïté de valeur de vérité 
    ingredients_val = recipe_row.get("ingredients", "")

    try:
        ingredients_list = ast.literal_eval(ingredients_val)
    except Exception:
        ingredients_list = str(ingredients_val).split(",")
    
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

    # PHASE A : Vérification des ingrédients interdits
    for r in restrictions_list:
        forbidden_list = forbidden_map.get(r, [])
        for bad_item in forbidden_list:
            if bad_item in ingredients_list:
                return False 

    # PHASE B : Vérification des tags (on a décidé de ne pas utiliser les tags car dans le jeu de données il y a souvant des tags manquants)
    #tags_val = recipe_row.get("tags")
    #if tags_val is not None and not pd.isna(tags_val):
    #    recipe_tags = [t.strip().lower() for t in str(tags_val).split(",")]
    #    for r in restrictions_list:
            # Si la restriction est 'vegan' mais que le tag 'vegan' n'est pas présent
    #         if r not in recipe_tags:
    #            return False */

    return True


class ActionGetIngredients(Action):
    def name(self) -> Text:
        return "action_get_ingredients"

    def run(self, dispatcher, tracker, domain):
        recipe_name = tracker.get_slot("recipe")
        
        # Fuzzy matching
        all_recipe_names = df_recipes["name"].tolist()
        closest_match = process.extractOne(recipe_name, all_recipe_names)
        if closest_match:
            recipe_name = closest_match[0] # permet de prendre en compte les typos

        # On récupère le DataFrame des correspondances
        matching_df = df_recipes[df_recipes["name"].str.lower() == recipe_name.lower()]

        if matching_df.empty:
            dispatcher.utter_message(f"Sorry, I couldn't find the recipe '{recipe_name}'.")
            return []
        
        # On extrait la PREMIÈRE ligne en tant que Series
        recipe_series = matching_df.iloc[0]
        
        restrictions = tracker.get_slot("dietary_restrictions") or "no"

        # On passe la Series à la fonction de vérification
        if not recipe_matches_restrictions(recipe_series, restrictions):
            dispatcher.utter_message(
                f"The recipe '{recipe_name}' does not respect your dietary restrictions : {restrictions}."
            )
            return []

        raw_ingredients = recipe_series["ingredients"]

        try:
            # Convertir le string "[ingredients]" à la liste [ingredients]
            ingredients_list = ast.literal_eval(raw_ingredients)
        except Exception:
            # fallback si pas bien formatté
            ingredients_list = [i.strip() for i in str(raw_ingredients).split(",")]
        
        formatted_ingredients = "\n".join([f"- {ing}" for ing in ingredients_list])

        dispatcher.utter_message(
            f"Here are the ingredients for {recipe_name}:\n{', '.join(formatted_ingredients)}"
        )

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
        #use fuzzy matching to find the closest recipe name
        all_recipe_names = df_recipes["name"].tolist()
        closest_match = process.extractOne(recipe_name, all_recipe_names)
        if closest_match:
            recipe_name = closest_match[0]

        recipe_row = df_recipes[df_recipes["name"].str.lower() == recipe_name.lower()]

        if recipe_row.empty:
            dispatcher.utter_message(f"Sorry, I couldn't find the recipe '{recipe_name}'.")
            return []

        # Extraire la liste des instructions (sous forme de string "[instructions]")
        raw_steps = recipe_row.iloc[0]["steps"]

        # Convertir le string des instructions en une liste "[instructions]" => [instructions]
        try:
            steps_list = ast.literal_eval(raw_steps)
        except (ValueError, SyntaxError):
            # Fallback
            steps_list = [raw_steps]

        # Formatter avec une dash et retour à la ligne apres chaque instruction
        formatted_instructions = "\n".join([f"- {step}" for step in steps_list])

        dispatcher.utter_message(text=f"Follow these steps for {recipe_name}:\n{formatted_instructions}")
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

        restrictions = tracker.get_slot("dietary_restrictions") or "no"

        user_text = tracker.get_slot("ingredients")
        if not user_text:
            dispatcher.utter_message("Please tell me the ingredients you have.")
            return []

        user_text = str(user_text).strip().lower()

        threshold = 60  # Seuil pour le score minimale acceptable (pour selectionner le recipe ayant le plus d'ingredients en commun avec ce que l'utilisateur dispose déja)

        matched_recipes = []
        for _, row in df_recipes.iterrows():

            # On élimine les recipes contenant des ingredients interdites pour l'utilisateur (s'il a des restrictions alimentaires)
            if not recipe_matches_restrictions(row, restrictions):
                continue

            recipe_text = str(row.get("ingredients", "")).strip().lower()
            if not recipe_text:
                continue

            # 3 scorers utiles en "texte vs texte"
            score_token_set = fuzz.token_set_ratio(user_text, recipe_text)
            score_partial = fuzz.partial_ratio(user_text, recipe_text)
            score = max(score_token_set, score_partial)

            if score >= threshold:
                matched_recipes.append((row["name"], score))

        if not matched_recipes:
            dispatcher.utter_message("Sorry, I couldn't find any recipes with those ingredients.")
            return []

        # rendre les top 5 recipes necessitants le plus d'ingredients dont l'utlisateur dispose déja
        matched_recipes.sort(key=lambda x: x[1], reverse=True)
        top = matched_recipes[:5] 

        msg = "Here are some recipes you can make with your ingredients:\n"
        for i, (name, score) in enumerate(top, 1):
            msg += f"{i}. {name} ({score:.0f}%)\n"
        msg += "Which one would you like to prepare?"

        dispatcher.utter_message(msg)
        return []