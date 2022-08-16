#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

from socket import timeout
import cv2
import pymongo
import logging
import urllib.request
import mainconfig as cfg
import opencvtest as ocv
import datetime
from prettytable import PrettyTable

from telegram import KeyboardButton, ParseMode, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyMarkup, Update
from telegram.ext import *

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
myclient = pymongo.MongoClient(cfg.dbhost)
mydb = myclient[cfg.db]
mycol = mydb["users"]
GAME, PLAYER, COZ = range(3)
score_regex='^(?:-?[0-9]{1,2}|bt)\s+(?:-?[0-9]{1,2}|bt)$'

def get_scorelist(coll, user_id):
    return list(coll.aggregate([
        {"$match": {"username":user_id}},
        {"$unwind":"$game4.round"},
        {"$project": {"date":"$game4.date",
                    "us":{"$cond":{"if":{"$eq":["$game4.round.bolt_us",0]},
                                    "then":"$game4.round.score_us",
                                    "else":{"$concat":["bt",{"$toString":"$game4.round.bolt_us"}]}}},
                    "them":{"$cond":{"if":{"$eq":["$game4.round.bolt_them",0]},
                                    "then":"$game4.round.score_them",
                                    "else":{"$concat":["bt",{"$toString":"$game4.round.bolt_them"}]}}}
                                    }},
    ]))

def get_sum(coll, user_id):
    return coll.aggregate([
        {"$match":{"username":user_id}},
        {"$project": {"game4.round": {'$cond':[{"$ne":[{"$size":"$game4.round"},0]},
                                        "$game4.round",
                                        [{"score_us":0,"score_them":0,"bolt_us":0,"bolt_them":0}]
                                        ]}}},
        {"$unwind":"$game4.round"},
        {"$group":{"_id":"$username",
                                "sum_us":{"$sum":"$game4.round.score_us"},
                                "sum_them":{"$sum":"$game4.round.score_them"},
                                "bolt_us":{"$sum":"$game4.round.bolt_us"},
                                "bolt_them":{"$sum":"$game4.round.bolt_them"}}}
    ]).next()

def get_last_score(coll, user_id):
    return coll.aggregate([
        {"$match": {"username":user_id}},
        {"$project": {"game4.round": {'$cond':[{"$ne":[{"$size":"$game4.round"},0]},
                                        "$game4.round",
                                        [{"score_us":0,"score_them":0,"bolt_us":0,"bolt_them":0}]
                                        ]}}},
        {"$project": {"round":{"$arrayElemAt":[{"$slice":["$game4.round",-1]},0]}}},
        {"$project": {"score_us":"$round.score_us","score_them":"$round.score_them"}}
    ]).next()

wrong_text_reply = "Error: Score must look like \n10 4\nor\nbt 16\nor\n19 bt\n/cancel to exit\n/newGame to delete previous score "

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def start(update, context):
    test = mycol.find_one({"username":update.message.from_user.id,"game4.round":{"$exists":"true"}})
    if test is not None:
        #regex_score_message(update,context)
        update.message.reply_text("This is your current score:")
        reply_scoreboard(update, context)
        update.message.reply_text("Continue or, use /new to reset score")
        return GAME
    else:
        return new_game(update, context)

def new_game(update, context):
    mycol.delete_many({"username":update.message.from_user.id})
    mycol.update_one({'username':update.message.from_user.id},
                    {'$set':{'game4.date':str(datetime.date.today()),'game4.round':[]}},
        upsert=True)
    update.message.reply_text("*NEW GAME*\n"
                "Type the score like '(your score) (their score)'\n"
                "Examples:\n"
                "10 6\n"
                "bt 16")
    return GAME

def cancel(update, context):
    return ConversationHandler.END

def score_undo_callback(update, context):
    test = mycol.find_one({'username':update.message.from_user.id,'game4.round':{'$size':1}})
    if test is None:
        update.message.reply_text("Last round has been removed")
        mycol.update_one({'username':update.message.from_user.id},{'$pop': {'game4.round':1}})
        reply_sum(update, context)
        return GAME
    else:
        update.message.reply_text("Last round has been removed, the scoreboard is empty")
        return new_game(update, context)

def score_regex_callback(update, context):
    user_id = update.message.from_user.id
    score_string = update.message.text
    score_split = score_string.split()
    presult = get_sum(mycol,user_id)
    if is_int(score_split[0]):
        score_us = int(score_split[0])
        bolt_us = 0
    else:
        score_us = 0
        if presult['bolt_us']%6 == 3:
            bolt_us = 3
            score_us = -10
        elif presult['bolt_us']%6 == 1:
            bolt_us = 2
        else:
            bolt_us = 1

    if is_int(score_split[1]):
        score_them = int(score_split[1])
        bolt_them = 0
    else:
        score_them = 0
        if presult['bolt_them']%6 == 3:
            bolt_them = 3
            score_them = -10
        elif presult['bolt_them']%6 == 1:
            bolt_them = 2
        else:
            bolt_them = 1

    mycol.update_one({'username':user_id},{'$push':{'game4.round':
                    {'score_us':score_us,'bolt_us':bolt_us,
                    'score_them':score_them,'bolt_them':bolt_them}}})
    reply_sum(update, context)
    reply_win(update, context)
    return GAME

def reply_win(update, context):
    levels = [151,101,51]
    sum_ = get_sum(mycol,update.message.from_user.id)
    last_score = get_last_score(mycol,update.message.from_user.id)
    if sum_['sum_us']>sum_['sum_them']:
        current = sum_['sum_us']
        secondary = sum_['sum_them']
        last = current - last_score['score_us']
        winner = "we"
    else:
        current = sum_['sum_them']
        secondary = sum_['sum_us']
        last = current - last_score['score_them']
        winner = "they"
    for level in levels:
        if current>=level and secondary<level and last<level:
            update.message.reply_text(winner+" are the winners over "+str(level))
            update.message.reply_text("/continue or start /new game?")
            break

def reply_sum(update, context):
    sum_ = get_sum(mycol,update.message.from_user.id)
    #sum_us = sum_['sum_us']
    #sum_them = sum_['sum_them']
    #last_us = last_score['score_us']
    #last_them = last_score['score_them']
    update.message.reply_text("Current score: "+str(sum_['sum_us'])+" "+str(sum_['sum_them']))
    #update.message.reply_text("Last sum: "+str(last_score['score_us'])+" "+str(last_score['score_them']))
    
def reply_scoreboard(update, context):
    user_id = update.message.from_user.id
    score_table = PrettyTable()
    score_table.field_names = ["us","them"]
    score_table.align["us"] = 'r'
    score_table.align["them"] = 'l'
    score_date = ""
    scorelist = get_scorelist(mycol,user_id)
    for x in scorelist:
        score_table.add_row([x["us"],x["them"]])
        score_date = x["date"]
    score_table.add_row(["====","===="])
    sum_ = get_sum(mycol,user_id)
    score_table.add_row([sum_["sum_us"],sum_["sum_them"]])

    update.message.reply_text(score_date+f'<pre>{score_table}</pre>', parse_mode=ParseMode.HTML)

def score_invalid(update, context):
    update.message.reply_text(wrong_text_reply)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def downloader(update, context):
    pat = context.bot.getFile(update.message.photo[2]['file_id'])['file_path']
    urllib.request.urlretrieve(pat,'test.jpg')
    pho = cv2.imread('test.jpg')
    crd = ocv.imgToCards(pho)
    print(crd)
    resp = "\U00002663: "+str(crd[0])+"\n"+"\U00002660: "+str(crd[1])+"\n"+\
    "\U00002666: "+str(crd[2])+"\n"+"\U00002665: "+str(crd[3])+"\n"
    update.message.reply_text(resp, reply_markup=None)
    context.bot.sendPhoto(chat_id=update.message.chat.id, photo=open('result.jpg','rb'))

def main():
    updater = Updater(cfg.token, use_context=True)
    dp = updater.dispatcher
    
    """Handlers"""
    score_invalid_handler = MessageHandler(Filters.text, score_invalid)
    score_regex_handler = MessageHandler(Filters.regex(score_regex),score_regex_callback)
    # log all errors
    dp.add_error_handler(error)

    conv_handler = ConversationHandler(
        entry_points= [CommandHandler(["start","continue"], start),
                        CommandHandler("new", new_game)],
        states= {
            GAME: [score_regex_handler,
                CommandHandler("scoreboard",reply_scoreboard),
                CommandHandler("undo",score_undo_callback)],
        },

        fallbacks= [
                    CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    dp.add_handler(conv_handler)
    # Start the Bot
    updater.start_polling()
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
