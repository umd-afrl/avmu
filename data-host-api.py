from flask import Flask, Response
from . import demo_simple
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

app = Flask(__name__)


def retrieve_current_avmu_figure():
    fig = demo_simple.get_current_plot()
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    yield output.getvalue()


@app.route('/')
def get_avmu_figure():
    return Response(retrieve_current_avmu_figure(), mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0');
