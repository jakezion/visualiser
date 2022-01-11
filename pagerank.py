import tkinter.filedialog
import warnings

import requests  # For making http requests
import validators  # For parsing URL's
from bs4 import BeautifulSoup  # For parsing HTML
import json
import time
import queue
import math
import threading
import asyncio
import tkinter as tk  # UI stuff
from tkinter import ttk  # More UI stuff (Progress bar)
from functools import partial

# DEFAULT VALUES
SaveLocation = ""
StartURL = "https://www.bbc.co.uk/"
Domain = "bbc.co.uk/"
IGNORE_DUPLICATE_LINKS = False
MAX_PAGES = 500
ITERATIONS = 100
REQUEST_DEBOUNCE = 0.01
DAMPENING = 0.15

Debounce = False
WorkThread = None
ProgressBarRef = None
topRef = None
progressQueue = queue.Queue()
Pages = {}


class Page:
    def __init__(self, URL):
        self.URL = URL
        self.IncomingLinks = []
        self.OutgoingLinks = []
        self.pr = 1.0

    def addIncomingLink(self, link):
        # Check if link already exists
        if IGNORE_DUPLICATE_LINKS:
            for existingLink in self.IncomingLinks:  # Remove Duplicate
                if existingLink.URL == link.URL:
                    return
        self.IncomingLinks.append(link)

    def addOutgoingLink(self, link):
        if IGNORE_DUPLICATE_LINKS:
            for existingLink in self.OutgoingLinks:  # Remove Duplicate
                if existingLink.URL == link.URL:
                    return
        self.OutgoingLinks.append(link)

    def calculateRank(self, d, n):
        pr_sum = 0
        for link in self.IncomingLinks:
            page = Pages[link.URL]
            pr_sum += page.pr / len(page.OutgoingLinks)
        # pr_sum = sum((page.pr/len(page.OutgoingLinks)) for page in self.IncomingLinks)
        random = d / n
        self.pr = random + (1 - d) * pr_sum

    pass


class Link:
    def __init__(self, URL):
        self.URL = URL
        # Check if Internal
        if Domain in URL:
            self.Internal = True
        else:
            self.Internal = False


async def GetHTML(URL):
    if len(Pages) > MAX_PAGES:
        return
    if URL in Pages:
        # Pages[URL].addIncomingLink(Link(URL))
        # print("Page Already Exists")
        return
    global progressQueue
    progressQueue.put(len(Pages))
    topRef.event_generate("<<Updated>>", when="tail")
    # print("Requesting: "+URL)
    CurrentPage = Page(URL)
    Pages[URL] = CurrentPage
    await asyncio.sleep(REQUEST_DEBOUNCE)  # I never ddos'ed nobody.
    r = requests.get(URL)  # GetRequest
    # print(r.content)#HTML Content
    # Parse using Beautiful Soup
    soup = None
    try:
        soup = BeautifulSoup(r.content, "html.parser")
    except Exception:
        warnings.warn("Unable to parse " + URL)
    if soup is None:
        return
    for tag in soup.findAll("a"):  # For each anchor tag
        link = tag.attrs.get("href")
        if link is None or link == "":  # Ignore if empty
            continue
        # Check if valid url
        if validators.url(link):
            pass
            # print(link)
        else:
            continue
            # warnings.warn(link)
        # Maybe add something here for relative URL's?
        # Add something to normalize http vs https
        link = link.split("?")[0]  # If get parameters only get stuff before it
        if link[len(link) - 1] != "/":
            link = link + "/"
        # Ignore selfpointing
        if link != URL:
            CurrentPage.addOutgoingLink(Link(link))
    print(URL + " Outgoing: " + str(len(CurrentPage.OutgoingLinks)))
    for link in CurrentPage.OutgoingLinks:
        if link.Internal:
            await GetHTML(link.URL)


def MainScraper():
    asyncio.run(GetHTML(StartURL))
    # Create Incoming Links from outgoing links
    for k, page in Pages.items():
        for link in page.OutgoingLinks:
            if link.URL in Pages:
                page2 = Pages[link.URL]
                page2.addIncomingLink(Link(page.URL))

    # Any page that has no outgoing, create links to their incoming one
    for k, page in Pages.items():
        if len(page.OutgoingLinks) == 0:
            for link in page.IncomingLinks:
                page.addOutgoingLink(Link(link.URL))

    # Destroy any links that go to pages we aren't mapping
    for k, page in Pages.items():
        NewOutgoingLinks = []
        for link in page.OutgoingLinks:
            if link.URL in Pages:
                NewOutgoingLinks.append(link)
        page.OutgoingLinks = NewOutgoingLinks

    for x in range(0, ITERATIONS):
        for _, page in Pages.items():
            page.calculateRank(DAMPENING, len(Pages))
    RankSum = 0
    PageList = []
    for k, page in Pages.items():
        PageList.append(page)

    PageList.sort(key=lambda x: x.pr, reverse=True)
    for page in PageList:
        # print(page)
        print(page.URL)
        RankSum += page.pr
        print("  Rank: " + str(page.pr))
        # print("  Outgoing: " + str(len(page.OutgoingLinks)))
        # print("  Incoming: " + str(len(page.IncomingLinks)))
    print("Rank Sum: " + str(RankSum))

    JSONPages = {}
    for page in PageList:
        PageData = {}
        PageData["URL"] = page.URL
        PageData["PageRank"] = page.pr
        PageData["OutgoingLinks"] = []
        PageData["IncomingLinks"] = []
        for link in page.OutgoingLinks:
            PageData["OutgoingLinks"].append(link.URL)
        for link in page.IncomingLinks:
            PageData["IncomingLinks"].append(link.URL)
        JSONPages[page.URL] = PageData
    FileName = ""
    DomainName = Domain.split(".", 1)[0]
    FileName = FileName + DomainName + "_" + str(MAX_PAGES)
    FileName = FileName + "_Json.txt"
    if SaveLocation != "":
        output = open(SaveLocation + "/" + FileName, "w")
    else:
        output = open("" + FileName, "w")
    Header = {}
    Header["StartURL"] = StartURL
    Header["Domain"] = Domain
    Header["MaxPages"] = MAX_PAGES

    json.dump({"Header": Header, "Data": JSONPages}, output, ensure_ascii=False)
    output.close()
    global Debounce
    Debounce = False  # Set Debounce to false at end of thread


def CreateWindow():
    top = tk.Tk()
    global topRef
    topRef = top
    top.title("Website Scraper + PageRank")
    InputBaseUrl = tk.StringVar()
    InputDomain = tk.StringVar()
    InputMaxPages = tk.StringVar()
    InputIterations = tk.StringVar()
    InputDebounce = tk.StringVar()
    InputIgnoreDuplicates = tk.IntVar()
    InputDampening = tk.StringVar()

    TitleLabel = tk.Label(top, text="Scraper Settings").grid(row=1, column=0, columnspan=2)

    URLLabel = tk.Label(top, text="Base URL: ").grid(row=2, column=0)
    URLEntry = tk.Entry(top, textvariable=InputBaseUrl)
    URLEntry.grid(row=2, column=1)
    URLEntry.insert(0, "www.bbc.co.uk")

    DomainLabel = tk.Label(top, text="Domain: ").grid(row=3, column=0)
    DomainEntry = tk.Entry(top, textvariable=InputDomain)
    DomainEntry.grid(row=3, column=1)
    DomainEntry.insert(0, "bbc.co.uk")

    MaxPagesLabel = tk.Label(top, text="Max Pages: ").grid(row=4, column=0)
    MaxPagesEntry = tk.Entry(top, textvariable=InputMaxPages)
    MaxPagesEntry.grid(row=4, column=1)
    MaxPagesEntry.insert(0, 100)

    DebounceLabel = tk.Label(top, text="Debounce: ").grid(row=5, column=0)
    DebounceEntry = tk.Entry(top, textvariable=InputDebounce)
    DebounceEntry.grid(row=5, column=1)
    DebounceEntry.insert(0, 1)

    TitleLabel = tk.Label(top, text="Pagerank Settings").grid(row=6, column=0, columnspan=2)

    IterationsLabel = tk.Label(top, text="Iterations: ").grid(row=7, column=0)
    IterationsEntry = tk.Entry(top, textvariable=InputIterations)
    IterationsEntry.grid(row=7, column=1)
    IterationsEntry.insert(0, 100)

    DampeningLabel = tk.Label(top, text="Dampening %: ").grid(row=8, column=0)
    DampeningEntry = tk.Entry(top, textvariable=InputDampening)
    DampeningEntry.grid(row=8, column=1)
    DampeningEntry.insert(0, 15)

    IgnoreDuplicatesLabel = tk.Label(top, text="Ignore Duplicate Links: ").grid(row=9, column=0)
    IgnoreDuplicatesCheck = tk.Checkbutton(top, text="", variable=InputIgnoreDuplicates, onvalue=1, offvalue=0)
    IgnoreDuplicatesCheck.grid(row=9, column=1)

    TitleLabel = tk.Label(top, text="Export Settings").grid(row=10, column=0, columnspan=2)

    SaveLocationLabel = tk.Label(top, text="JSON Save Location: ").grid(row=11, column=0)
    SaveLocationButton = tk.Button(top, text="Location", command=SaveCallBack).grid(row=11, column=1)

    CallBackPartial = partial(RunCallBack, InputBaseUrl, InputDomain, InputMaxPages, InputIterations, InputDebounce)
    RunButton = tk.Button(top, text="Run", command=CallBackPartial).grid(row=12, column=0, columnspan=2)

    ProgressBar = ttk.Progressbar(top, orient="horizontal", mode="determinate", length=320)
    ProgressBar.grid(row=13, column=0, columnspan=2)
    ProgressBar.config(value=0, maximum=0)
    global ProgressBarRef
    ProgressBarRef = ProgressBar
    global progressQueue
    handler = partial(on_update, progressQueue=progressQueue, ProgressBarRef=ProgressBarRef)
    top.bind("<<Updated>>", handler)
    top.mainloop()


def on_update(event, progressQueue, ProgressBarRef):  # Progress Bar Updater
    ProgressBarRef["maximum"] = MAX_PAGES
    ProgressBarRef["value"] = progressQueue.get()


def SaveCallBack():  # Save Button Callback
    value = tkinter.filedialog.askdirectory()
    global SaveLocation
    SaveLocation = value
    print("Save Location Set As: " + value)
    pass


def RunCallBack(InputBaseUrl, InputDomain, InputMaxPages, InputIterations, InputDebounce):  # Run button callback
    global Debounce
    if Debounce is True:
        print("Debouce is True")
        return
    Debounce = True
    # Clear Pages + Progress queue
    global Pages
    Pages = {}

    print("Test")
    print("URL: " + InputBaseUrl.get())
    # Check valid URL
    global StartURL
    if validators.url(InputBaseUrl.get()):
        StartURL = InputBaseUrl.get()
    print("Domain: " + InputDomain.get())
    # Check valid Domain

    global Domain
    if InputDomain.get() in StartURL:
        Domain = InputDomain.get()
    else:
        print("Domain was invalid, using default.")
    print("MAX Pages: " + InputMaxPages.get())
    # Check valid int
    if InputMaxPages.get().isdigit():
        global MAX_PAGES
        MAX_PAGES = int(InputMaxPages.get())
    else:
        print("MaxPages was invalid, using default.")

    print("Iterations: " + InputIterations.get())
    # Check valid int
    if InputIterations.get().isdigit():
        global ITERATIONS
        ITERATIONS = int(InputIterations.get())
    else:
        print("ITERATIONS was invalid, using default.")

    print("Debounce: " + InputDebounce.get())
    # Check valid int
    if InputDebounce.get().isdigit():
        global REQUEST_DEBOUNCE
        REQUEST_DEBOUNCE = int(InputDebounce.get()) / 10
    else:
        print("ITERATIONS was invalid, using default.")

    print("Save Location: " + SaveLocation)
    # Check valid filepath

    # Put this on seperate thread
    global WorkThread
    WorkThread = threading.Thread(target=MainScraper).start()


CreateWindow()


# TODO turn into class
def visualiser_jake(dataset):
    inputData = open(dataset)
    jsonData = json.load(inputData)
    LinkArray = []
    NodeArray = []
    jsonData = jsonData["Data"]

    def writeToJson(attribute, array):
        counter = 0
        output.write('"' + attribute + '": [\n')
        for row in array:
            json.dump(row, output, ensure_ascii=False)
            if counter != (len(array) - 1): output.write(',\n')
            counter += 1
        output.write('\n]')

    group = 0
    for line in jsonData.values():
        group += 1
        outgoingLinks = line['OutgoingLinks']
        outgoingLinksValue = len(outgoingLinks)
        sourceNode = line['URL']
        sourceNodeRank = line['PageRank'] * 1000  # make pagerank a reasonable size
        # SORTS URL, COLOUR and SIZE
        NodeArray.append({"id": sourceNode, "group": group, "rank": sourceNodeRank})

        # SORTS SOURCE->TARGET (for d3 link visualisation)
        if outgoingLinksValue > 0:
            for targetNode in outgoingLinks:
                LinkArray.append({"source": sourceNode, "target": targetNode, "value": "1"})
        else:
            LinkArray.append({"source": sourceNode, "target": sourceNode, "value": "0"})

    output = open("results/results.json", "w")
    output.write("{\n")
    writeToJson("NodeArray", NodeArray)
    output.write(",\n")
    writeToJson("links", LinkArray)
    output.write("\n}")
    output.close()
