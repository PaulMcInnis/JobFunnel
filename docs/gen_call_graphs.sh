# Install pyan3 via pip3 install pyan3 and then you can do below:
echo "building call graph .dot files in ./call_graphs"

mkdir ./call_graphs
pyan3 jobfunnel/backend/tools/filters.py -c --dot > ./call_graphs/filters.dot
pyan3 jobfunnel/backend/scrapers/indeed.py -c --dot > ./call_graphs/indeed.dot
pyan3 jobfunnel/backend/jobfunnel.py -c --dot > ./call_graphs/jobfunnel.dot

echo "Done."
# Then you can visualize the created files with graphviz by making svg, or you
# can copypaste their contents here and look online: http://www.webgraphviz.com/
