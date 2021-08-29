# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction
from rasa_sdk.events import SlotSet, AllSlotsReset, UserUtteranceReverted
import json
import random
import re

class ActionDefaultFallback(Action):
    """Executes the fallback action and goes back to the previous state
    of the dialogue"""

    def name(self) -> Text:
        return "action_default_fallback"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(response="utter_please_rephrase")

        # Revert user message which led to fallback.
        return [UserUtteranceReverted()]

class ShowQuestionAction(Action):
    """Executes the fallback action and goes back to the previous state
    of the dialogue"""

    def name(self) -> Text:
        return "action_show_question"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        question = None
        answer = None
        if tracker.slots.get("question") is None:
            file = open("actions/api_utils/questions.json")
            questionsJson = json.load(file)
            questions = questionsJson["problems"]
            qna = questions[random.randint(0,len(questions)-1)]
            question=qna.get("question")
            answer = qna.get("answer")
        else:
            question = tracker.slots.get("question")
            answer = tracker.slots.get("valid_answer")
        buttonDetails = {
            "Hint" : "/user.request_hint",
            "Submit": answer
        }
        buttons = []
        for button in buttonDetails:
            buttons.append(
                {
                    "title": "{}".format(button),
                    "payload": buttonDetails[button],
                }
            )
        dispatcher.utter_message(
            text= "Solve "+str(question)+"\n You can request hint at any time",
            buttons=buttons
        )
        return [SlotSet("question", question), SlotSet("valid_answer",answer)]

class AnswerSubmitAction(Action):
    """Executes the fallback action and goes back to the previous state
    of the dialogue"""

    def name(self) -> Text:
        return "action_check_answer"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        valid_answer = float(tracker.slots.get("valid_answer"))
        user_answer = float(tracker.slots.get("answer"))
        if valid_answer is not None and round(user_answer,2) == round(valid_answer,2):
            dispatcher.utter_message(response= "utter_you_did_it")
        else:
            dispatcher.utter_message(text="Oh NO! Wrong Answer.")
        dispatcher.utter_message(response= "utter_ask_another_problem")
        return [AllSlotsReset()]

class InavlidExpressionException(Exception):
    pass

class SolveProblemForm(Action):

    def name(self) -> Text:
        return "action_solve_problem"
    
    
    def validate_expression(self,
                            value: Text,
                            dispatcher: CollectingDispatcher,
                            tracker: Tracker,):
        print("recieved expression - ", value)
        if type(value) is not list:
            value = [value]
        print(value)
        for expression in value:
            try:
                eval(expression)
                if expression.isnumeric():
                    raise InavlidExpressionException
                else:
                    return expression
            except InavlidExpressionException:
                expression = self.solve_again(tracker.latest_message.get('text'))
            except SyntaxError:
                expression = self.solve_again(tracker.latest_message.get('text'))
            except ZeroDivisionError:
                expression = None
                dispatcher.utter_message(response= "utter_invalid_division")
            except Exception:
                expression = None
                dispatcher.utter_message(
                        response="utter_invalid_expression",
                    )
            return expression

    def solve_again(self,msg):
        reg = re.findall(r'[0-9.]+|[*/+\-\^\(\)]', msg)
        expression = ''.join(reg)
        return expression

    def run(self,
               dispatcher: CollectingDispatcher,
               tracker: Tracker,
               domain: Dict[Text, Any]) -> List[Dict]:
        question = self.validate_expression(tracker.get_slot("expression"),dispatcher, tracker)
        if question is not None:
            try:
                answer = eval(question)
            except Exception:
                answer = None
            if answer is not None:
                dispatcher.utter_message(
                    text= "Here you go! Answer is "+str(round(answer,2)),
                )
            else:
                dispatcher.utter_message(
                    response="utter_invalid_expression"
                )
        return [AllSlotsReset()]