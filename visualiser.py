import json
import sys
import webbrowser


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

    output = open("results/results.js", "w")
    output.write("let json = {\n")
    writeToJson("nodes", NodeArray)
    output.write(",\n")
    writeToJson("links", LinkArray)
    output.write("\n}")
    output.close()
    webbrowser.open_new_tab('display.html')



if __name__ == "__main__":
    dataset = sys.argv[1]
    visualiser_jake(dataset)
