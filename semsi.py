from flask import Blueprint, Flask, Response, request, jsonify, make_response
from lexicon.stemming import Stemmer

MAX_DOCUMENT_LENGTH = 200000

api = Blueprint('api', __name__)
stemmer = Stemmer(language="fi")

@api.route('/stem', methods=['POST', 'GET'])
def stem():
    if request.method == 'POST':
        d = request.form
    else:
        d = request.args
    text = d.get('text', '').strip()
    if len(text) > MAX_DOCUMENT_LENGTH:
        err = 'Document too big (max. %d chars)' % MAX_DOCUMENT_LENGTH
        return make_response(err, 400)

    if not text:
        return jsonify(response='')

    res = stemmer.convert_string(text)
    return jsonify(response=res)

app = Flask(__name__)
app.register_blueprint(api, url_prefix='/v1')

if __name__ == "__main__":
    app.run(debug=True)
