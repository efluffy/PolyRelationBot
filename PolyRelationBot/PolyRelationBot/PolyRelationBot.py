#!/usr/bin/env python
"""
Telegram bot to graph relationships between people
"""
# Author: Adrian Aiken (adaiken@outlook.com)

import json
import logging
from telegram.ext import Updater, CommandHandler, Job
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import networkx as nx
import os
import pickle

class RelationNode:
    def __init__(self, name1, name2, relationship):
        names = [name1, name2]
        names.sort()

        self.name1 = names[0]
        self.name2 = names[1]
        self.relationship = relationship

    def equals(self, other):
        if (self.name1.lower() == other.name1.lower()) or (self.name1.lower() == other.name2.lower()):
            if (self.name2.lower() == other.name1.lower()) or (self.name2.lower() == other.name2.lower()):
                return True
        return False

    def hasName(self, name):
        return name.lower() == self.name1.lower() or name.lower() == self.name2.lower()

    def getOtherName(self, name):
        if name.lower() == self.name1.lower():
            return self.name2
        return self.name1

    def __str__(self):
        return "[" + self.name1 + "] and [" + self.name2 + "] are [" + self.relationship + "]"

######################################################
###### Startup - needs to be present every time ######
######################################################
logger = logging.getLogger()
logger.setLevel(logging.INFO)

with open('Config.json', 'r') as configfile:
    config = json.load(configfile)
with open('Strings.json', 'r') as stringsfile:
    strings = json.load(stringsfile)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

nodes = set()

def saveNodes():
    f = file(config["nodes_file"], "w")
    pickle.dump(nodes, f)
    f.close()

if not os.path.exists(config["nodes_file"]):
    saveNodes()

f = file(config["nodes_file"])
nodes = pickle.load(f)

###########################
#### Graph Managemenet ####
###########################
def addNode(name1, name2, relationship):
    newNode = RelationNode(name1, name2, relationship)
    oldNode = next((x for x in nodes if newNode.equals(x)), None)

    if oldNode is not None:
        nodes.remove(oldNode)

    nodes.add(newNode)
    saveNodes()

def removeNode(name1, name2):
    newNode = RelationNode(name1, name2, "")
    oldNode = next((x for x in nodes if newNode.equals(x)), None)

    if oldNode is not None:
        nodes.remove(oldNode)

    saveNodes()

def getEdges(name):
    visited = []
    toVisit = [name]
    edges = []

    while len(toVisit) is not 0:
        curName = toVisit.pop()
        visited.append(curName)

        curNodes = [n for n in nodes if n.hasName(curName)]
        for node in curNodes:
            nodeName = node.getOtherName(curName)
            if not nodeName.lower() in map(unicode.lower, visited):
                edges.append(node)
                toVisit.append(nodeName)

    return edges, visited

#######################
#### Graph Drawing ####
#######################
def generateGraph(name):
    edges, nodes = getEdges(name)
    relations = dict()
    labels = dict()

    G = nx.Graph()
    G.clear()
    for edge in edges:
        G.add_edge(edge.name1.lower(), edge.name2.lower())
        relations[(edge.name1.lower(), edge.name2.lower())] = edge.relationship

    for node in nodes:
        labels[node.lower()] = node

    pos = nx.spring_layout(G)

    plt.cla()
    plt.axis('off')
    nx.draw_networkx_nodes(G, pos, node_size = 1400)
    nx.draw_networkx_edges(G, pos)
    nx.draw_networkx_edge_labels(G, pos, relations)
    nx.draw_networkx_labels(G, pos, labels)

    plt.savefig(config["graph_file"])

###############################################
#### Telegram message handling and parsing ####
###############################################
def addRelationship(bot, update):
    m = update.message.text.replace("/add ", "")

    if m.find(" + ") == -1 or m.find(" = ") == -1:
        bot.sendMessage(update.message.chat_id, text = strings["error_add"])
        return

    name1 = m[:m.lower().find(" + ")]
    relationship = m[m.lower().find(" = ") + 3:]
    name2 = m[m.lower().find(" + ") + 3:m.lower().find(" = ")]
    
    if relationship.lower() in config["remove_words"]:
        removeRelationship(bot, update)
        return

    if name1.lower() in config["self_words"]:
        name1 = "@" + update.message.from_user.username
    if name2.lower() in config["self_words"]:
        name2 = "@" + update.message.from_user.username

    addNode(name1, name2, relationship)
    bot.sendMessage(update.message.chat_id, text = strings["added"].format(name1, name2, relationship))
        
def removeRelationship(bot, update):
    if update.message.text.find(", ") == -1:
        bot.sendMessage(update.message.chat_id, text = strings["error_add"])
        return

    m = update.message.text.replace("/remove ", "").split(", ")
    name1 = m[0]
    name2 = m[1]

    if name1.lower() in config["self_words"]:
        name1 = "@" + update.message.from_user.username
    if name2.lower() in config["self_words"]:
        name2 = "@" + update.message.from_user.username

    removeNode(name1, name2)
    bot.sendMessage(update.message.chat_id, text = strings["removed"].format(name1, name2))

def showRelationship(bot, update, args):
    if len(args) == 0:
        name = "@" + update.message.from_user.username
    else:
        name = unicode(args[0])
        if name.lower() in config["self_words"]:
            name = "@" + update.message.from_user.username

    generateGraph(name)
    photofile = open(config["graph_file"].encode("utf-8"), "rb")
    bot.sendPhoto(update.message.chat_id, photofile)

def showHelp(bot, update):
    bot.sendMessage(update.message.chat_id, text = strings["help"])

####################
#### Main stuff ####
####################
def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def main():
    updater = Updater(config["bot_token"])
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("add", addRelationship))
    dp.add_handler(CommandHandler("remove", removeRelationship))
    dp.add_handler(CommandHandler("show", showRelationship, pass_args = True))
    dp.add_handler(CommandHandler("help", showHelp))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
