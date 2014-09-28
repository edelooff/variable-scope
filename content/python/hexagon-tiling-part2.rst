Hexagon tilings with Python - Part 2
####################################

:tags: Python, drawing, PIL, aggdraw
:status: draft

In part one, we covered the drawing of smooth, ant-aliased hexagons in a grid-like fashion. In this post, we will extend that beginning into a program to draw hexagon fills that can be used for tiled background. The key improvements that were identified in the previous post:

1. Canvas sizing and shape wrapping
2. Color wrapping around the edges
3. Configurable, mostly random coloring

Canvas sizing and shape wrapping
================================

To be able to use the generated image as a tiled background, the shapes must wrap from left to right. That is, if the left edge of a row shows a pentagon that lacks a small fraction, the right edge of the row should end with that fraction.

This is a complex way of saying that the width of the image must be an exact multiple of the pattern size. The pattern in this case is the smallest shape from which a repeating pattern can be constructed. For the hexagons generator we have, this pattern is one column wide and two rows tall.

Because the pattern size is very closely coupled to the dimensions of the hexagon, we make this information available as a property of :py:`class HexagonGenerator`. We then modify the existing script to draw only outlines so we can see how things are constructed:

.. code-block:: python
    :linenos: table

    class HexagonGenerator(object):
      # Rest of class as previously defined
      @property
      def pattern_size(self):
        return self.col_width, self.row_height * 2

    def main():
      hexagon_generator = HexagonGenerator(40)
      width, height = hexagon_generator.pattern_size
      image = Image.new('RGB', (int(width * 2), int(height * 3)), 'white')
      draw = Draw(image)
      draw.rectangle((0, 0, width, height), Brush('black', opacity=64))
      colors = (('red', 'blue'), ('green', 'purple'))
      for row in range(5):
        for col in range(3):
          hexagon = hexagon_generator(row, col)
          color = colors[row % 2][col % 2]
          draw.polygon(list(hexagon), Pen(color, width=3))
      draw.flush()
      image.show()

.. figure:: {filename}/images/hexagon-tiling/hexagon_autosized.png
    :align: right
    :alt: A tiled set of 4x3 hexagons, arranged on a automatically sized canvas.

    Resulting hexagons. The gray rectangle indicates the pattern size.

    Clearly illustrated in this image is how the lines of each row of hexagons overlap the ones from the preceding row. This effect can be reduced by adding an alpha-channel to the lines.

The hexagon generator is initialized to generate hexagons of a 40px edge length. The :py:`width` and :py:`height` of the pattern are then used to create a canvas that is two patterns wide and three tall. This makes for a reasonably square canvas where we can demonstrate a few things.

First, a plain rectangle indicating the pattern size is drawn. Then, five rows of three columns each are drawn. The number of (full) rows we can fit is twice the number of patterns, minus one. This is due to the rows only shifting up half a pattern size at a time. The hexagons in the even rows are then drawn in alternating red and blue, those in the odd rows in green and purple.


Iteration variations
--------------------

What becomes clear upon inspection of the result is how the overlapping lines are drawn. The first hexagon, drawn in red, has its lower right line drawn over in green by the next rows' hexagon. The exact order in which this occurs can be influenced by changing the order in which iteration happens:

* Sequential row -> column iteration
* Sequential column -> row iteration
* Random row -> column iteration
* Iteration that draws in inward/outward hexagonal patterns

Generating these different iteration patterns is outside the scope of this post, but may prove an interesting thing to play with for certain projects.


Delegating image creation
-------------------------

In the previous examples we've done a fair bit of hand-waving when it comes to determining the size of the canvas. By now, with the canvas creation becoming more involved, it makes sense to take another good look at the requirements and create a new function that satisfies these.

The function should accept a 2-tuple that contains the size of the pattern, and the desired number of repetitions. From this, a canvas should be created that is as close to square as possible. The returned value shall be an instance of :py:`class Image`:

.. code-block:: python
    :linenos: table

    def create_canvas(pattern_size, repetitions):
      """Returns an Image that fits the given number of pattern repetitions."""
      width, height = pattern_size
      canvas_width = int(repetitions * width)
      canvas_height = int(round(canvas_width / height) * height)
      return Image.new('RGB', (canvas_width, canvas_height), 'white')

For this use-case, the pattern will always be wider than taller, so the canvas size is determined by the number of horizontal repetitions. Once that is determined, the height is chosen as the number of repetitions that brings the resulting canvas closest to a square.

Extending the function to work with patterns of different aspect ratio is left as an exercise for the reader.


Color wrapping around the image edges
=====================================

To demonstrate correct color wrapping, we first have to change the coloring process a bit, introducing a function to generate random colors. The following will produce random, distinct colors across most of the RGB spectrum. The cutoff points for individual channel level are chosen so that we don't end up with too pale or dark colors, but otherwise it's pretty straightforward:

.. code-block:: python
    :linenos: table

    def random_color():
      """Returns a random RGB color from a space of 343 options."""
      levels = range(32, 256, 32)
      return tuple(random.choice(levels) for _ in range(3))

We can then use these colors for use in ``Pen`` or ``Brush`` classes. Note that the return value must be a tuple. A list of three values will not be accepted as a color by either class and the default black is used.

Using this random color function we get some.. *colorful* results:

.. code-block:: python
    :linenos: table

    def main():
      hexagon_generator = HexagonGenerator(40)
      width, height = hexagon_generator.pattern_size
      image = Image.new('RGB', (int(width * 2), int(height * 3)), 'white')
      draw = Draw(image)
      for row in range(7):
        for col in range(2):
          hexagon = hexagon_generator(row, col)
          draw.polygon(list(hexagon), Brush(random_color()))
      draw.flush()
      image.show()

.. figure:: {filename}/images/hexagon-tiling/hexagon_random_fill.png
    :align: right
    :alt: A tiling of randomly colors hexagons.

    Result of our random coloring

    One of the better results after a dozen runs. Random coloring is a nice idea, but something to restrict the range of hue or saturation would greatly improve the result.



..  _aggdraw: http://effbot.org/zone/pythondoc-aggdraw.htm
..  _anti-grain geometry: http://antigrain.com/about/index.html
..  _pil: http://effbot.org/imagingbook/
..  _regular tiling: http://en.wikipedia.org/wiki/Tiling_by_regular_polygons#Regular_tilings
