import os
from flask import Flask, make_response, render_template, request
import random
import cairosvg

app = Flask(__name__)

colorlist = ['"#17BF00"', '"#FF9E19"', '"#F33131"', '"#C21F1F"']

@app.route("/test.html")
def test():
    return render_template('test.html')

@app.route("/")
def hello():
    return "Hello World!"

@app.route('/images/test.png')
def serve_content(svgFile=None):
    output = ''
    try:
        with open(os.path.join(app.root_path, 'roadmap.svg'), 'r') as file_obj:
            for oneline in file_obj:
                stringindex = oneline.find('<g')
                if stringindex == -1:
                    output += oneline
                    continue
                stringindex = oneline.find('id')
                if stringindex == -1:
                    output += oneline
                    continue
                tempstring = oneline[stringindex:]
                randomint = random.randint(0, len(colorlist)-1)
                onelist = oneline.split(' ')
                outputstr = onelist[0] + ' ' + onelist[1] + ' ' + 'fill=' + colorlist[randomint] + '>\n'
                output += outputstr
    
        with open(os.path.join(app.root_path, 'images/test.png'), 'wb') as file_output:
            cairosvg.svg2png(output, write_to=file_output)
        
        with open(os.path.join(app.root_path, 'images/test.png')) as f:
            response = make_response(f.read())
            response.headers['Content-Type'] = 'image/png'
            return response
    except:
        abort(make_response("dumped", 400))

@app.route('/templated.svg')
def templated_svg():
    "Example using a template in the templates directory."
    width = request.args.get('width', '800')
    height = request.args.get('height', '600')
    svg = render_template('roadmap.svg', width=width, height=height)
    response = make_response(svg)
    response.content_type = 'image/svg+xml'
    return response


@app.route('/database.svg')
def database_svg():
    "Example using a string stored somewhere."
    # Read in ./images/letters.svg.
    svg = open(os.path.join(app.root_path, 'images', 'roadmap.svg')).read()
    response = make_response(svg)
    #response.content_type = 'image/svg+xml'
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
