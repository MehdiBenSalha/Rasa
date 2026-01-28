from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher


from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher



class ActionGetIngredients(Action):
    def name(self) -> Text:
        return "action_get_ingredients"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        ingredients = ["flour", "sugar", "butter", "eggs", "vanilla extract"]
        dispatcher.utter_message(f"Here are the ingredients: {', '.join(ingredients)}")
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
        instructions = [
            "1. Preheat oven to 350°F",
            "2. Mix flour and sugar",
            "3. Add butter and eggs",
            "4. Stir in vanilla extract",
            "5. Bake for 30 minutes"
        ]
        dispatcher.utter_message(f"Follow these steps:\n" + "\n".join(instructions))
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
        dispatcher.utter_message("Your recipe is complete! Enjoy your cooking!")
        return []
