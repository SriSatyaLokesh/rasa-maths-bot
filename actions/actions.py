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
import logging as logger

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
    """Shows question when user wants to practice"""

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
        # If question slot is empty i.e., user asked for question freshly get from DB or file. else get from slot
        if tracker.slots.get("question") is None:
            file = open("actions/api_utils/questions.json")
            questionsJson = json.load(file)
            questions = questionsJson["problems"]
            qna = questions[random.randint(0,len(questions)-1)]
            question=qna.get("question")
            answer = qna.get("answer")
            logger.info(f'Asked Question {qna}')
        else:
            # if we are showing question after showing hint
            question = tracker.slots.get("question")
            answer = tracker.slots.get("valid_answer")
            # we can improve "HINT" by providing question specific hint getting from DB
        buttonDetails = {
            "Hint" : "/user.request_hint",
            "Submit" : answer
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
        # we weill use these two slots in action_check_answer
        return [SlotSet("question", question), SlotSet("valid_answer",answer)]

class AnswerSubmitAction(Action):
    """When user submits answer to the given question"""

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
        try:
            if valid_answer is not None and round(user_answer,2) == round(valid_answer,2):
                dispatcher.utter_message(response= "utter_you_did_it")
            else:
                dispatcher.utter_message(text="Oh NO! Wrong Answer.")
        except Exception as err:
            logger.error(f'failed to check answer - {err}')
            dispatcher.utter_message(response="bot_down")
        dispatcher.utter_message(response= "utter_ask_another_problem")
        return [AllSlotsReset()]

class InavlidExpressionException(Exception):
    """To validate when whether expression is really invalid"""
    pass

class SolveProblemForm(Action):

    def name(self) -> Text:
        return "action_solve_problem"
    
    
    def validate_expression(self,
                            value: Text,
                            dispatcher: CollectingDispatcher,
                            tracker: Tracker,):
        logger.info(f'DIET extracted {value} as expression')
        if type(value) is not list:
            value = [value]
        # if we get more than one entity
        for expression in value:
            try:
                expression = self.solve_again(tracker.latest_message.get('text'))
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
                dispatcher.utter_message(response="utter_invalid_expression")
            return expression

    def solve_again(self,msg):
        """Will extract enity from the user message, if DIET fails to extract"""
        reg = re.findall(r'[0-9.]+|[*/+\-\^\(\)]', msg)
        expression = ''.join(reg)
        logger.info(f'manually indentified the expression {expression} from {msg}')
        return expression

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict]:
        question = self.validate_expression(tracker.get_slot("expression"),dispatcher, tracker)
        # validate the expression before evaluating the answer
        if question is not None:
            try:
                answer = eval(question)
            except Exception as err:
                logger.error(f'error while evaluating user question {err}')
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