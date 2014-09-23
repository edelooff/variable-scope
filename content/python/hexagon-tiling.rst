Hexagon tilings with Python
###########################

:date: 2014-09-23
:tags: Python, drawing, PIL, aggdraw
:status: draft

A few days ago I ended up on a website (I forgot where) which featured a very nice and subtle square tiling on the background of the page. Now, this is in itself is not astonishing, plenty of folks and businesses out there will present you with all sorts of tessellated backgrounds. However, it got me thinking about doing some tiling background myself. Not because I particularly need one (it certainly wouldn't look right on this blog), but just to experiment. To make things slightly more interesting I opted for another shape: *the hexagon*.

A hexagon is a polygon with six edges and six vertices. The *regular* hexagon is equilateral and all internal angles are 120°. It is also one of three polygons with which you can create a `regular tiling`_. That is, using only hexagons a plane can be filled without any gaps or overlaps. The other two regular shapes with which this can be done are the square and the equilateral triangle.

Drawing a hexagon with PIL
==========================

The first goal to achieving a tiling is to create a single hexagon. The first stop when it comes to images in Python is the *Python Imaging Library* (better known as PIL_). Using this library and knowledge of basic math, the following code will generate a single hexagon:

.. code-block:: python
    :linenos: table

    import math
    from PIL import Image, ImageDraw

    def hexagon_generator(edge_length, offset):
      """Generator for coordinates in a hexagon."""
      x, y = offset
      for angle in range(0, 360, 60):
        x += math.cos(math.radians(angle)) * edge_length
        y += math.sin(math.radians(angle)) * edge_length
        yield x, y

    def main():
      image = Image.new('RGB', (100, 100), 'white')
      draw = ImageDraw.Draw(image)
      hexagon = hexagon_generator(40, offset=(30, 15))
      draw.polygon(list(hexagon), outline='black', fill='red')
      image.show()

.. figure:: {filename}/images/hexagon-tiling/hexagon_pil.png
    :align: right
    :alt: A hexagon with a zoomed section showing aliasing on the slanted edges

    The hexagon drawn with PIL.

    Because of the lack of anti-aliasing, the slanted lines of the hexagon look very messy. A close-up of one of the vertices shows this in more detail.

Step by step:

1. We create a 100x100 pixel image in RGB color mode with a pristine white background.
2. We initialize a Draw instance on this, and start drawing a polygon.
3. The hexagon_generator function yields six coordinates. Starting from the top-left vertex it calculates the next coordinate-pair and yields this. With the sixth iteration, the top-left vertex is yielded and the polygon is closed.
4. We draw the polygon in red with a black outline, and then show it using whatever platform bindings are present. Alternatively the image can be saved and then opened with an external viewer.

However, as shown, the resulting image is not very visually appealing. The slanted edges of the hexagon are not smoothed, anti-aliased, and drawing multiple hexagons will cause gaps and overlaps because our hexagons are not on exact pixel boundaries. This is problematic and needs a solution. Thankfully, one exists.

Drawing a hexagon with aggdraw
==============================

Aggdraw_ is an extension to PIL based on the `Anti-Grain Geometry`_ library which provides anti-aliasing and alpha compositing. After installing aggdraw [#install_aggdraw]_ and making few minor adjustments to the script, the resulting hexagon is perfectly smooth along the edges:

.. code-block:: python
    :linenos: table
    :hl_lines: 3 11 12 16 18 19

    import math
    from PIL import Image
    from aggdraw import Draw, Brush, Pen

    def hexagon_generator(edge_length, offset):
      """Generator for coordinates in a hexagon."""
      x, y = offset
      for angle in range(0, 360, 60):
        x += math.cos(math.radians(angle)) * edge_length
        y += math.sin(math.radians(angle)) * edge_length
        yield x
        yield y

    def main():
      image = Image.new('RGB', (100, 100), 'white')
      draw = Draw(image)
      hexagon = hexagon_generator(40, offset=(30, 15))
      draw.polygon(list(hexagon), Pen('black'), Brush('red'))
      draw.flush()
      image.show()

.. figure:: {filename}/images/hexagon-tiling/hexagon_aggdraw.png
    :align: right
    :alt: A hexagon with a zoomed section showing anti-aliased slanted edges

    The same hexagon as before, drawn with PIL+aggdraw.

    The slanted edges now look smooth and straight, and the 5x magnification shows the anti-aliasing that has been performed.

The highlighted changes:

* Importing the necessary aggdraw parts: Draw, Pen and Brush classes;
* The aggdraw :py:`polygon()` method requires a flattened list of coordinates rather than 2-tuples that are allowed by PIL;
* The drawing layer is created using aggdraw than PIL's ImageDraw;
* The polygon is colored using Pen and Brush classes (which may come in any order);
* Importantly, the draw instance *must* be flushed, or the image will remain blank.


Footnotes
=========

..  [#install_aggdraw] Installing ``aggdraw`` turned out to be a small challenge. The C++-extension in the version available on PyPI seems to have a problem compiling on 64-bit systems. What worked for me (but may cause subtle problems) was prefixing CFLAGS to the build command. ``CFLAGS="-fpermissive" python setup.py install`` in my ``env/build`` directory after having ``pip install aggdraw`` fail.

..  _aggdraw: http://effbot.org/zone/pythondoc-aggdraw.htm
..  _anti-grain geometry: http://antigrain.com/about/index.html
..  _pil: http://effbot.org/imagingbook/
..  _regular tiling: http://en.wikipedia.org/wiki/Tiling_by_regular_polygons#Regular_tilings
