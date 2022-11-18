import time
import datetime
import json
import requests
import re
from Base.ThreadObject import ThreadObject


class WetterOnline(ThreadObject):
    '''
    classdocs
    '''
    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded(["weatherUrl"])


    def getSonnenStunden(self):
        now = datetime.datetime.now()

        tabellenName = "table id=\"sun"
        sucheBeenden = "<\/tr>"
        tabellenTeil = "tr id=\"asd24"
        # <td data-tt-args="[&quot;Donnerstag, 16.07.&quot;,0]"
        tabellenDatum = r"""td data-tt-args=\"\[&quot;(.+)&quot;"""
        # <div>\n  0 h\n </div>\n
        #tabelleSonnenStunden = r"""<div>\n(.+)\n\s+</div>"""
        tabelleSonnenStunden = r"""<div>"""
        #tabelleSonnenStunden = r"""\S\s\S"""

        """
        
        This is the text which will be parsed.
        
        
        
      </tbody>
     </table>
    
     <!-- Sonnenscheindauer, Aufgang und Untergang, UV -->
     <table id="sun">
        <tbody>    
        
        ...
        
            </tr>
        <tr id="asd24">
            <td data-tt-args="[&quot;Freitag, 17.07.&quot;,0]" data-tt-function="TTasdwrapper">
     <div>
      5 h
     </div>
     <span class="label">Sonnenstunden</span>
    </td>
    <td data-tt-args="[&quot;Samstag, 18.07.&quot;,1]" data-tt-function="TTasdwrapper">
     <div>
      7 h
     </div>
     <span class="label">Sonnenstunden</span>
    </td>
    <td data-tt-args="[&quot;Sonntag, 19.07.&quot;,2]" data-tt-function="TTasdwrapper">
     <div>
      6 h
     </div>
     <span class="label">Sonnenstunden</span>
    </td>
    <td data-tt-args="[&quot;Montag, 20.07.&quot;,3]" data-tt-function="TTasdwrapper">
     <div>
      13 h
     </div>
     <span class="label">Sonnenstunden</span>
    </td>
    """


        # hole website
        v = requests.get(self.configuration["weatherUrl"])
        
        # konvertiere von bytes zu string
        webstring = v.content.decode('utf-8')

        # mache eine Liste mit den einzelnen Zeilen
        li = webstring.splitlines()
        
        
        richtigeTabelleGefunden = False
        richtigeTabellenTeilGefunden = False
        tabelleDatumGefunden = False
        tabelleSonnenStundenGefunden = False
        tag = 0
        wetterDaten = {}
        datum = ""
        sonnenStunden = ""
        
        for line in li:
        
            if re.findall(tabellenName, line):
                self.logger.debug(self, "Tabelle gefunden")
                #myPrint(line)
                richtigeTabelleGefunden = True
            
            if richtigeTabelleGefunden:
                
                if re.findall(tabellenTeil, line):
                    richtigeTabellenTeilGefunden = True
                    self.logger.debug(self, "TabellenTeil gefunden")
                    
                if richtigeTabellenTeilGefunden:
                    #myPrint(line)
                    match = re.findall(tabellenDatum, line)
                    if match:
                        self.logger.debug(self, "Datum gefunden")
                        datum = match[0]
                        tabelleDatumGefunden = True
      
                if tabelleSonnenStundenGefunden:
                    sonnenStunden = line
                    tabelleSonnenStundenGefunden = False
                    tabelleDatumGefunden = False
                    tempDate = datum.split()
                    temp = tempDate[1].split(".")
                    extDay = int(temp[0])
                    extMonth = int(temp[1])
                    tempSun = sonnenStunden.split()
                    if extMonth == now.month:
                        if (extDay == now.day):
                            wetterDaten["Tag_0"] = {}
                            wetterDaten["Tag_0"]["Sonnenstunden"] = int(tempSun[0])
                            wetterDaten["Tag_0"]["Datum"] = tempDate[1]
                        elif (extDay == now.day + 1):
                            tag = 1
                            wetterDaten["Tag_1"] = {}
                            wetterDaten["Tag_1"]["Sonnenstunden"] = int(tempSun[0])
                            wetterDaten["Tag_1"]["Datum"] = tempDate[1]                  
                        elif (extDay == now.day + 2):
                            tag = 2
                            wetterDaten["Tag_2"] = {}
                            wetterDaten["Tag_2"]["Sonnenstunden"] = int(tempSun[0])
                            wetterDaten["Tag_2"]["Datum"] = tempDate[1]     
                        elif (extDay == now.day + 3):
                            tag = 3
                            wetterDaten["Tag_3"] = {}
                            wetterDaten["Tag_3"]["Sonnenstunden"] = int(tempSun[0])
                            wetterDaten["Tag_3"]["Datum"] = tempDate[1]      
                        elif (extDay == now.day + 4):
                            tag = 4
                            wetterDaten["Tag_4"] = {}
                            wetterDaten["Tag_4"]["Sonnenstunden"] = int(tempSun[0])
                            wetterDaten["Tag_4"]["Datum"] = tempDate[1]      
                    elif extMonth == now.month + 1 or (now.month == 12 and extMonth == 1):
                            tag = tag + 1
                            wetterDaten["Tag_%i"%tag] = {}
                            wetterDaten["Tag_%i"%tag]["Sonnenstunden"] = int(tempSun[0])
                            wetterDaten["Tag_%i"%tag]["Datum"] = tempDate[1]                             
                    self.logger.debug(self, "Datum: %s" %datum)
                    self.logger.debug(self, "Sonne: %s" %sonnenStunden)
                    self.logger.debug(self, "******")

                if tabelleDatumGefunden:
                    match = re.findall(tabelleSonnenStunden, line)
                    if match:
                        match = re.findall(tabelleSonnenStunden, line)
                        if match:
                            self.logger.debug(self, "Sonnenstunden gefunden")
                            tabelleSonnenStundenGefunden = True
                        
            if re.findall(sucheBeenden, line) and richtigeTabellenTeilGefunden:
                richtigeTabelleGefunden = False
                richtigeTabellenTeilGefunden = False
                tabelleDatumGefunden = False
    
        return wetterDaten

    def threadInitMethod(self):
        self.wetterdaten = {"lastrequest":0}
        self.initWeather = True

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

        publishWeather = False
        now = datetime.datetime.now()

        # Wir wollen das Wetter um 15 und um 6 Uhr holen
        if (now.hour == 14 and self.wetterdaten["lastrequest"] != 14) or (now.hour == 5 and self.wetterdaten["lastrequest"] != 5) or (now.hour == 19 and self.wetterdaten["lastrequest"] != 19) or self.initWeather:
            self.initWeather = False
            self.wetterdaten["lastrequest"] = now.hour
            publishWeather = True
            try:
                self.wetterdaten.update(self.getSonnenStunden())
                #tempWetter = getSonnenStunden()
                #self.wetterdaten.update( (k,v) for k,v in tempWetter.items() if v is not None)
            except:
                self.logger.error(self, "Wetter Daten konnten nicht geholt werden! getSonnenStunden() fehlerhaft")

        # Wenn der Tag_1 dem aktuellen Tag entspricht dann müssen wir die Tage um eins verrutschen
        # wir fragen zurest ab ob der key vorhanden ist denn es kann sein dass das Dict leer ist.
        if "Tag_1" in self.wetterdaten: 
            tempDate = self.wetterdaten["Tag_1"]["Datum"].split(".")
            if now.day == int(tempDate[0]):
                publishWeather = True
                if "Tag_1" in self.wetterdaten:
                    self.wetterdaten["Tag_0"] = self.wetterdaten["Tag_1"]
                if "Tag_2" in self.wetterdaten:
                    self.wetterdaten["Tag_1"] = self.wetterdaten["Tag_2"]
                if "Tag_3" in self.wetterdaten:
                    self.wetterdaten["Tag_2"] = self.wetterdaten["Tag_3"]
                if "Tag_4" in self.wetterdaten:
                    self.wetterdaten["Tag_3"] = self.wetterdaten["Tag_4"]
                # Wir füllen von hinten mit None auf
                self.wetterdaten["Tag_4"] = None

        if publishWeather:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.wetterdaten, globalPublish = True, enableEcho = False)


    def threadBreak(self):
        time.sleep(30)