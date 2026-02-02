import pandas as pd
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from rapidfuzz import process, fuzz

from pathlib import Path 
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "test.csv"
df_recipes = pd.read_csv(DATA_PATH)  


from typing import List, Dict

def recipe_matches_restrictions(recipe_row, restrictions: List[str]) -> bool:
    if not restrictions or restrictions == "no":
        return True

    restrictions = [r.lower() for r in restrictions]
    ingredients_str = recipe_row.iloc[0]["ingredients"] 
    ingredients_list = [i.strip() for i in ingredients_str.split(",")]
    
    # On definit un dictionnaire des ingredients restreint pour les restrictions alimentaires les plus communs
    forbidden_map: Dict[str, List[str]] = {
        "vegetarian": ["chicken", "beef", "pork", "bacon", "steak", "lamb", "duck", "turkey", "fish", "shrimp", "gelatin"],
        "vegan": ["milk", "cheese", "egg", "butter", "honey", "cream", "yogurt", "whey", "chicken", "beef", "pork", "fish", "lard"],
        "halal": ["pork", "bacon", "ham", "lard", "gelatin", "alcohol", "wine", "beer"],
        "gluten-free": ["flour", "wheat", "barley", "rye", "bread", "pasta", "couscous", "semolina", "malt"],
        "dairy-free": ["milk", "cheese", "butter", "cream", "yogurt", "whey", "casein", "lactose"],
        "pescatarian": ["chicken", "beef", "pork", "bacon", "steak", "lamb", "duck", "turkey"],
        "nut-free": ["peanut", "almond", "walnut", "cashew", "pecan", "hazelnut", "pistachio"],
        "lactose-intolerant": ["milk", "cheese", "butter", "cream", "yogurt", "whey", "curds", "lactose", "casein", "malted milk", "milk powder", "condensed milk", "evaporated milk", "sour cream", "kefir"],
        "kosher": ["pork", "bacon", "ham", "lard", "rabbit", "gelatin","shrimp", "crab", "lobster", "clam", "mussel", "oyster", "scallop", "eel", "squid"]
    }

    # PHASE A : Verification des ingredients
    for r in restrictions:
        forbidden_list = forbidden_map.get(r, [])
        for bad_item in forbidden_list:
            if bad_item in ingredients_list:
                # On a trouvé un ingredient restreint, on retourne false
                return False

    # --- PHASE B : Verifier les tags
    if "tags" in recipe_row:
        tags = [t.strip().lower() for t in str(recipe_row["tags"]).split(",")]
        for r in restrictions:
            if r not in tags:
                # Si on ne trouve pas un des tags attendus on retourne false
                return False

    return True


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

        all_recipe_names = df_recipes["name"].tolist()
        closest_match = process.extractOne(recipe_name, all_recipe_names)
        if closest_match:
            recipe_name = closest_match[0]

        recipe_row = df_recipes[df_recipes["name"].str.lower() == recipe_name.lower()]

        if recipe_row.empty:
            dispatcher.utter_message(f"Sorry, I couldn't find the recipe '{recipe_name}'.")
            return []
        
        # Recuperer les restrictions alimentaires de l'utilisateur
        restrictions = tracker.get_slot("dietary_restrictions") or ["no"]
        print ("User restrictions:", restrictions)

        # Récupérer les ingrédients
        ingredients_str = recipe_row.iloc[0]["ingredients"] 
        ingredients_list = [i.strip() for i in ingredients_str.split(",")]

        if not recipe_matches_restrictions(recipe_row, restrictions):
            dispatcher.utter_message(
                f"The recipe '{recipe_name}' does not respect your dietary restrictions."
            )
            return []

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
        #use fuzzy matching to find the closest recipe name
        all_recipe_names = df_recipes["name"].tolist()
        closest_match = process.extractOne(recipe_name, all_recipe_names)
        if closest_match:
            recipe_name = closest_match[0]

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

        restrictions = tracker.get_slot("dietary_restrictions") or "no"

        user_text = tracker.get_slot("ingredients")
        if not user_text:
            dispatcher.utter_message("Please tell me the ingredients you have.")
            return []

        # user_text peut être une liste ou un texte selon ton pipeline → on force en string
        if isinstance(user_text, list):
            user_text = ", ".join([str(x) for x in user_text if x])
        user_text = str(user_text).strip().lower()

        threshold = 60  # en texte-vs-texte, souvent plus bas que liste-vs-liste (teste 50-75)

        matched_recipes = []
        for _, row in df_recipes.iterrows():

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

        matched_recipes.sort(key=lambda x: x[1], reverse=True)
        top = matched_recipes[:5]

        msg = "Here are some recipes you can make with your ingredients:\n"
        for i, (name, score) in enumerate(top, 1):
            msg += f"{i}. {name} ({score:.0f}%)\n"
        msg += "Which one would you like to prepare?"

        dispatcher.utter_message(msg)
        return []