# Natural Language Toolkit: Chatbot Utilities
#
# Copyright (C) 2001-2016 NLTK Project
# Authors: Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

# Based on an Eliza implementation by Joe Strout <joe@strout.net>,
# Jeff Epler <jepler@inetnebr.com> and Jez Higgins <jez@jezuk.co.uk>.
#from __future__ import print_function

import re
import random
from py_execute.process_executor import execute
from mock import Mock


reflections = {
  "i am"       : "you are",
  "i was"      : "you were",
  "i"          : "you",
  "i'm"        : "you are",
  "i'd"        : "you would",
  "i've"       : "you have",
  "i'll"       : "you will",
  "my"         : "your",
  "you are"    : "I am",
  "you were"   : "I was",
  "you've"     : "I have",
  "you'll"     : "I will",
  "your"       : "my",
  "yours"      : "mine",
  "you"        : "me",
  "me"         : "you"
}


class Chat(object):
    def __init__(self, pairs, reflections={}):
        """
        Initialize the chatbot.  Pairs is a list of patterns and responses.  Each
        pattern is a regular expression matching the user's statement or question,
        e.g. r'I like (.*)'.  For each such pattern a list of possible responses
        is given, e.g. ['Why do you like %1', 'Did you ever dislike %1'].  Material
        which is matched by parenthesized sections of the patterns (e.g. .*) is mapped to
        the numbered positions in the responses, e.g. %1.

        :type pairs: list of tuple
        :param pairs: The patterns and responses
        :type reflections: dict
        :param reflections: A mapping between first and second person expressions
        :rtype: None
        """
        self._pairs = []
        for p in pairs:
            x,y,z = (p[0],None,p[1]) if len(p)==2 else p[:3]
            z=tuple((i,self._condition(i)) for i in z)
            if y:
                self._pairs.append((re.compile(x, re.IGNORECASE),re.compile(y, re.IGNORECASE),z))
            else:
                self._pairs.append((re.compile(x, re.IGNORECASE),y,z))
        self._reflections = reflections
        self._regex = self._compile_reflections()
        self._memory = {"genral":{}}
        self.conversation = {"genral":[]}
        self.sessionID = "genral"
        self.attr = {"genral":{"match":None,"pmatch":None}}
    
    def _startNewSession(self,sessionID):
        self._memory[sessionID]={}
        self.conversation[sessionID]=[]
        self.attr[sessionID]={"match":None,"pmatch":None}

    def _restructure(self,group,index=None):
        if index==None:
            toremove={}
            allElem = list(group)
            for i in group:
                toremove[i]=set()
                for j in group[i]:
                    toremove[i].update(set(group[i]).intersection(group[j]))
            for i in group:
                for j in toremove[i]:
                    group[i].remove(j)
                    try: allElem.remove(j)
                    except: pass
            index = list(group)
            toremove = [j for i in list(allElem) for j in group[i]]
            for i in toremove:
                try: allElem.remove(i)
                except: pass
        else:
            allElem = list(index)
        while index:
            i = index.pop()
            if type(group[i])==list:
                group[i] = self._restructure(dict(group),group[i])
                for j in list(group[i]):
                    try: index.remove(j)
                    except: pass
        return {i:group[i] for i in allElem}
        
    def _subAction(self,group,start_end_pair,action):
        return {i:{
                    "action":action[i],
                    "start":start_end_pair[i][0],
                    "end":start_end_pair[i][1],
                    "child":self._subAction(group[i],start_end_pair,action)
                  } for i in group}
    
    def _getWithin(self,group,index):
        i=0
        orderedGroup = []
        while i<len(index):
            if group[index[i]]["action"]=="if":
                group[index[i]]["within"]=[]
                orderedGroup.append(group[index[i]])
                i+=1
                startIF = True 
                while startIF:
                    if i>=len(index):
                        raise SyntaxError("If not closed in Conditional statement")
                    if group[index[i]]["action"]=="elif":
                        group[index[i]]["within"]=[]
                        orderedGroup.append(group[index[i]])
                        i+=1
                    elif group[index[i]]["action"]=="else":
                        group[index[i]]["within"]=[]
                        orderedGroup.append(group[index[i]])
                        i+=1
                        startIF = False
                        pos = i
                        while group[index[pos]]["action"]!="endif":
                            pos,within = self._getWithin(group,index[pos:])
                            group[index[i-1]]["within"].append(within)
                            pos=pos+i
                        i=pos
                        group[index[i]]["within"]=[]
                        orderedGroup.append(group[index[i]])
                        i+=1
                    elif group[index[i]]["action"]=="endif":
                        group[index[i]]["within"]=[]
                        orderedGroup.append(group[index[i]])
                        i+=1
                        startIF= False
                    else:
                        pos,within = self._getWithin(group,index[i:])
                        group[index[i-1]]["within"].append(within)
                        for i in range(i,pos):
                            del group[index[i]]
                        i=pos+i
            #elif group[index[i]]["action"]=="for":
            #    group[index[i]]["within"]=[]
            #    orderedGroup.append(group[index[i]])
            #    i+=1
            #    startFor = True
            #    while startFor:
            #        if i>=len(index):
            #            raise SyntaxError("for not closed in Conditional statement")
            #        if group[index[i]]["action"]=="endfor":
            #            i+=1
            #            startFor = False
            #        else:
            #            pos,within = self._getWithin(group,index[i:])
            #            group[index[i-1]]["within"].append(within)
            #            for i in range(i,pos):
            #                del group[index[i]]
            #            i=pos+i
            #elif group[index[i]]["action"]=="while":
            #    group[index[i]]["within"]=[]
            #    orderedGroup.append(group[index[i]])
            #    i+=1
            #    startwhile = True
            #    while startFor:
            #        if i>=len(index):
            #            raise SyntaxError("while not closed in Conditional statement")
            #        if group[index[i]]["action"]=="endwhile":
            #            i+=1
            #            startFor = False
            #        else:
            #            pos,within = self._getWithin(group,index[i:])
            #            group[index[i-1]]["within"].append(within)
            #            for i in range(i,pos):
            #                del group[index[i]]
            #            i=pos+i   
            #elif group[index[i]]["action"]=="split":
            #    orderedGroup.append(group[index[i]])
            #    i+=1
            #elif group[index[i]]["action"]=="=":
            #    orderedGroup.append(group[index[i]])
            #    i+=1
            elif group[index[i]]["action"] == "chat":
                orderedGroup.append(group[index[i]])
                i+=1
            elif group[index[i]]["action"] == "low":
                orderedGroup.append(group[index[i]])
                i+=1
            elif group[index[i]]["action"] == "up":
                orderedGroup.append(group[index[i]])
                i+=1
            elif group[index[i]]["action"] == "cap":
                orderedGroup.append(group[index[i]])
                i+=1
            else:
                return i,orderedGroup
        return i,orderedGroup
                
    def _setwithin(self,group):
        old =group
        for i in group:
            if group[i]["child"]:
                group[i]["child"] = self._setwithin(group[i]["child"])
        index = list(group)
        index.sort(lambda x,y: cmp(group[x]["start"],group[y]["start"]))
        pos,orderedGroup = self._getWithin(group,index)
        if pos<len(index):
            print old
            raise SyntaxError("in valid statement")
        return orderedGroup
    
    def _inherit(self,start_end_pair,action):
        group = {}
        for i in range(len(start_end_pair)):
            group[i] = []
            for j in range(len(start_end_pair)):
                if start_end_pair[i][0]<start_end_pair[j][0] and start_end_pair[i][1]>start_end_pair[j][1]:
                    group[i].append(j)
        group = self._restructure(group)
        group = self._subAction(group,start_end_pair,action)
        return self._setwithin(group)

    def _condition(self,response):
        pos = [m.start(0) for m in re.finditer(r'{%|%}', response)]
        newPos = [start for start in pos if (not start) or response[start-1]!="\\" ]
        i=0
        start_end_pair = []
        while newPos:
            for i in range(1,len(newPos)):
                if response[newPos[i]+1] == "}":
                    break
            if response[newPos[i-1]] == "{":
                end,start = newPos.pop(i),newPos.pop(i-1)+2
                start_end_pair.append((start,end))
            else:
                raise SyntaxError("invalid syntax")
        actions = []
        for start,end in start_end_pair:
            #statement = re.findall(r'^[\s\t]*(if|for|while|split|=|endif|endfor|endwhile|elif|else|chat|low|up|cap)[\s\t]+',response[start,end])
            statement = re.findall(r'^[\s\t]*(if|endif|elif|else|chat|low|up|cap)[\s\t]+',response[start:end])
            if statement:
                actions.append(statement[0])
            else:
                raise SyntaxError("invalid statement '%s'" % response[start:end] )
        group = self._inherit(start_end_pair,actions)
        return group
    
    def _compile_reflections(self):
        sorted_refl = sorted(self._reflections.keys(), key=len,
                reverse=True)
        return  re.compile(r"\b({0})\b".format("|".join(map(re.escape,
            sorted_refl))), re.IGNORECASE)

    def _substitute(self, str):
        """
        Substitute words in the string, according to the specified reflections,
        e.g. "I'm" -> "you are"

        :type str: str
        :param str: The string to be mapped
        :rtype: str
        """

        return self._regex.sub(lambda mo:
                self._reflections[mo.string[mo.start():mo.end()]],
                    str.lower())
        
    def _mapSolve(self,response,start,end,sessionID = "genral"):
        think=0
        if response[start+1] != "!":
            s=response[start+1:end].strip().split(":")
        else:
            think=1
            s=response[start+2:end].strip().split(":")
        name = s[0]
        i=0
        for i in range(1,len(s)):
            if name[-1]=="\\":
                name += ":"+s[i]
            else:
                i-=1
                break
        i+=1
        name = name.strip().lower()
        if i<(len(s)):
            value = s[i]
            for i in range(i+1,len(s)):
                if value[-1]=="\\":
                    value += ":"+s[i]
                else:
                    break
            self._memory[sessionID][name] = self._substitute(value.strip())
        if think or not name in self._memory[sessionID]:
            return ""
        return self._memory[sessionID][name]
    
    def _map(self,response,sessionID = "genral"):
        pos = [m.start(0) for m in re.finditer(r'[{}]', response)]
        newPos = [start for start in pos if (not start) or response[start-1]!="\\" ]
        i=0
        while newPos:
            for i in range(1,len(newPos)):
                if response[newPos[i]] == "}":
                    break
            if response[newPos[i-1]] == "{":
                start,end = newPos[i-1],newPos[i]
                substitution = self._mapSolve(response,start,end,sessionID =sessionID)
                diff = len(substitution) - (end-start+1)
                for j in range(i+1,len(newPos)):
                    newPos[j] += diff
                newPos.pop(i)
                newPos.pop(i-1)
                response = response[:start] + substitution + response[end+1:]
            else:
                raise SyntaxError("invalid syntax")
        return response
    
    def _evalSolve(self,response,start,end,sessionID = "genral"):
        think=0
        cmdStart = start+1
        if response[cmdStart] == "!":
            think=1
            cmdStart += 1
        cmd = response[cmdStart:end]
        cmd = self._map(cmd,sessionID =sessionID)
        result = execute(cmd, ui=Mock())
        if result[0]:
            raise SystemError("%d\n%s" % result)
        if think:
            return ""
        return result[1].replace("{","\{").replace("}","\}")
    
    def _eval(self,response,sessionID = "genral"):
        match=self.attr[sessionID]["match"]
        parentMatch=self.attr[sessionID]["pmatch"]
        finalResponse = ""
        prev =0
        for m in re.finditer(r'%[0-9]+', response):
            start = m.start(0)
            end = m.end(0)     
            num = int(response[start+1:end])
            finalResponse = response[prev:start] + \
                self._substitute(match.group(num))
            prev = end
        if parentMatch!=None:
            response = finalResponse + response[prev:]
            finalResponse = ""
            prev =0
            for m in re.finditer(r'%![0-9]+', response):
                start = m.start(0)
                end = m.end(0)            
                num = int(response[start+2:end])
                finalResponse = response[prev:start] + \
                    self._substitute(parentMatch.group(num))
                prev = end
        response = finalResponse + response[prev:]
        pos = [m.start(0) for m in re.finditer(r'[\[\]]', response)]
        newPos = [start for start in pos if (not start) or response[start-1]!="\\" ]
        i=0
        while newPos:
            for i in range(1,len(newPos)):
                if response[newPos[i]] == "]":
                    break
            if response[newPos[i-1]] == "[":
                start,end = newPos[i-1],newPos[i]
                substitution = self._evalSolve(response,start,end,sessionID =sessionID)
                diff = len(substitution) - (end-start+1)
                for j in range(i+1,len(newPos)):
                    newPos[j] += diff
                newPos.pop(i)
                newPos.pop(i-1)
                response = response[:start] + substitution + response[end+1:]
            else:
                raise SyntaxError("invalid syntax")
        return self._map(response,sessionID =sessionID).replace("\{","{").replace("\}","}")
    
    def _checkIF(self,con,sessionID = "genral"):
        #con = self._eval(con,sessionID =sessionID)
        pos = [(m.start(0),m.end(0),m.group(0)) for m in re.finditer(r'([\<\>!=]=|[\<\>]|&|\|)', con)]
        if not pos:
            return con.strip()
        res = True
        prevres = None
        prevO = None
        A = con[0:pos[0][0]].strip()
        for j in  range(len(pos)):
            s,e,o = pos[j]
            try:
                B = con[e:pos[j+1][0]].strip()
            except:
                B = con[e:].strip()
            try:
                a = float(A)
                b = float(b)
            except:
                a = A
                b = B
            if o=="|":
                if prevres == None:
                    prevres = res 
                elif prevres == True:
                    return True
                else:
                    prevres = (prevres or res)
            elif o=="&":
                if prevres == None:
                    prevres = res 
                elif prevres == False:
                    return False
                else:
                    prevres = (prevres and res)
            else:
                if o=="!=":
                    res = (a!=b)
                elif o=="==":
                    res = (a==b)
                elif o=="<=":
                    res = (a<=b)
                elif o=="<":
                    res = (a<b)
                elif o==">=":
                    res = (a>=b)
                elif o==">":
                    res = (a>b)
            A = B
        return res
    
    def _checkAndEvalveCondition(self, response,condition,startIndex=0,endIndex=None,sessionID = "genral"):
        finalResponse = ""
        i=0
        while i < len(condition):
            pos =  condition[i]["start"]-2
            finalResponse += self._eval(response[startIndex:pos],sessionID =sessionID)
            if condition[i]["action"] == "if":
                start = condition[i]["start"]+re.compile("([\s\t]*if[\s\t]+)").search(response[condition[i]["start"]:]).end(1)
                end = condition[i]["end"]
                check = True
                matchedIndex = None
                while check:
                    con = self._checkAndEvalveCondition(response,condition[i]["child"],start,end,sessionID =sessionID)
                    i+=1
                    if self._checkIF(con,sessionID =sessionID):
                        matchedIndex = i-1
                        while condition[i]["action"] != "endif":
                            i+=1
                        check = False
                    elif condition[i]["action"] == "else":
                        matchedIndex = i
                        while condition[i]["action"] != "endif":
                            i+=1
                        check = False                        
                    elif condition[i]["action"] == "elif":
                        start = condition[i]["start"]+re.compile("[\s\t]*elif[\s\t]+").search(response[condition[i]["start"]:]).end(0)
                        end = condition[i]["end"]
                    elif condition[i]["action"] == "endif":
                        check = False     
                finalResponse += self._checkAndEvalveCondition(
                                        response,
                                        condition[matchedIndex]["within"],
                                        condition[matchedIndex]["end"]+2,
                                        condition[matchedIndex+1]["start"]-2,
                                        sessionID =sessionID
                                        ) if matchedIndex!=None else ""
            elif condition[i]["action"] == "chat":
                start = condition[i]["start"]+re.compile("([\s\t]*chat[\s\t]+)").search(response[condition[i]["start"]:]).end(1)
                finalResponse += self.respond(self._checkAndEvalveCondition(
                                        response,
                                        condition[i]["child"],
                                        start,
                                        condition[i]["end"],
                                        sessionID =sessionID
                                        ))
            elif condition[i]["action"] == "low":
                start = condition[i]["start"]+re.compile("([\s\t]*low[\s\t]+)").search(response[condition[i]["start"]:]).end(1)
                finalResponse += self._checkAndEvalveCondition(
                                        response,
                                        condition[i]["child"],
                                        start,
                                        condition[i]["end"],
                                        sessionID =sessionID
                                        ).lower()
            elif condition[i]["action"] == "up":
                start = condition[i]["start"]+re.compile("([\s\t]*up[\s\t]+)").search(response[condition[i]["start"]:]).end(1)
                finalResponse += self._checkAndEvalveCondition(
                                        response,
                                        condition[i]["child"],
                                        start,
                                        condition[i]["end"],
                                        sessionID =sessionID
                                        ).upper()
            elif condition[i]["action"] == "cap":
                start = condition[i]["start"]+re.compile("([\s\t]*cap[\s\t]+)").search(response[condition[i]["start"]:]).end(1)
                finalResponse += self._checkAndEvalveCondition(
                                        response,
                                        condition[i]["child"],
                                        start,
                                        condition[i]["end"],
                                        sessionID =sessionID
                                        ).capitalize()
            #elif condition[i]["action"] == "for":
            #elif condition[i]["action"] == "while":
            #elif condition[i]["action"] == "split":
            #elif condition[i]["action"] == "=":
            startIndex = condition[i]["end"]+2
            i+=1
        finalResponse += self._eval(response[startIndex:endIndex if endIndex != None else len(response)],sessionID =sessionID)
        return finalResponse
            
    
    def _wildcards(self, response, match, parentMatch,sessionID = "genral"):
        self.attr[sessionID]["match"]=match
        self.attr[sessionID]["pmatch"]=parentMatch
        response,condition =  response
        return self._checkAndEvalveCondition(response,condition,sessionID =sessionID )

    def respond(self, str,sessionID = "genral"):
        """
        Generate a response to the user input.

        :type str: str
        :param str: The string to be mapped
        :rtype: str
        """

        # check each pattern
        for (pattern, parent, response) in self._pairs:
            match = pattern.match(str)
            parentMatch = parent.match(self.conversation[sessionID][-2]) if parent!=None else True
            # did the pattern match?
            if parentMatch and match:
                parentMatch = None if parentMatch==True else parentMatch
                resp = random.choice(response)    # pick a random response
                resp = self._wildcards(resp, match, parentMatch) # process wildcards
    
                # fix munged punctuation at the end
                if resp[-2:] == '?.': resp = resp[:-2] + '.'
                if resp[-2:] == '??': resp = resp[:-2] + '?'
                return resp

    # Hold a conversation with a chatbot

    def converse(self,firstQuetion=None ,quit="quit",sessionID = "genral"):
        if firstQuetion!= None:
            self.conversation[sessionID].append(firstQuetion)
            print firstQuetion
        input = ""
        while input != quit:
            input = quit
            try: input = raw_input(">")
            except EOFError:
                print input
            if input:
                self.conversation[sessionID].append(input)
                while input[-1] in "!.": input = input[:-1]
                self.conversation[sessionID].append(self.respond(input))
                print self.conversation[sessionID][-1]


