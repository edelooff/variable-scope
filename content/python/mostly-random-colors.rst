Creating a mostly-random color generator
########################################

:tags: Python, random
:status: draft

.. figure:: {filename}/images/hexagon-tiling/hexagons_random_rgb.png
    :align: right
    :alt: Grid of randomly colored hexagons

    Fully randomized colors

    A coloring like this may be ideal for some situations, but mostly it's too... *random*.

In the previous two posts we've exlored how to draw hexagons and how to tile them and create images that can be seamlessly repeated. We also briefly covered coloring them using a random color generator. The coloring process itself worked fine, but many times the created tiling turned out not very visually appealing, the colors of too harsh a contrast in tone and brightness.

In this post we'll cover the creation of a mostly-random color generator. One that creates random colors within a certain fraction of the available colorspace.


Picking a color representation
==============================

There are a different ways to represent colors in RBG colorspace, providing us with different ways in which to restrict the available portion to select random colors from:

* *RGB*: Red, Green and Blue values -- certainly the most straightforward way
* *HSV*: Hue, Saturation, Value (brightness) -- Cylindrical color mapping, common in color wheels in various graphics programs
* *HSL*: Hue, Saturation and Lightness -- Cylindrical color mapping similar to HSV with a few different behaviors

Any of the above could be used, and all three have potentially interesting behavior when certain values are kept constant, or only allowed to vary by a small amount. If we would like a behavior where we can restrict the *hue* of the color but have full variation in lightness and color intensity, the direct RGB mode is ruled out.

The choice between HSV and HSL mostly comes down to a matter of taste. Intuitively, when I read a color where all three channels are maxed, I would expect that to be a fully saturated and maximally intense color. HSV gives us that result, where HSL gives us full white (the maximum chroma is achieved at :py:`L=0.5`). For this reason, let's take HSV as our color coordinate system.


HSV to RGB in Python
====================

Conveniently, Python comes with a library that does transitions between different color coordinate mappings of RGB. The colorsys_ library contains a pair of functions to convert between RGB and HSV (as well as HSL and YIQ). There is a small catch though: all inputs and outputs are floating point numbers between 0 and 1, rather than the 0-255 integers we typically see for RGB.

The reason for this is simply that there is no rule that RGB has strictly 8 bits per channel. in the 90's, 16 bit color modes were common, where *red*, *green* and *blue* were represented by 5, 6, and 5 bits respectively. Digital camera's operating in RAW mode typically record 10, 12 or even 14 bit per channel worth of color information. [#raw]_

PIL works with 8-bits per channel colors, so we need a pair of simple converters between the 0-255 integer and 0-1 floating point domains:

.. code-block:: python

    import colorsys

    def to_float(value, domain=255):
      return float(value) / domain

    def from_float(value, domain=255):
      return int(round(value * domain))

    rgb = 10, 150, 255
    hsv = colorsys.rgb_to_hsv(*map(to_float, rgb))
    print hsv  # (0.5714285714285715, 0.9607843137254902, 1.0)
    rgb = map(from_float, colorsys.hsv_to_rgb(*hsv))
    print rgb  # [10, 150, 255]


Building the randomizer
=======================

Let's build a simple randomizing function where can lock down the hue. To make the function slightly friendlier to our human inputs, we'll accept hue inputs as degrees, mimicing the color circle as commonly seen in image editing software.

.. code-block:: python

    import colorsys
    import random

    def random_color(hue=None, sat=None, val=None):
      hue = hue / 360.0 if hue is not None else random.random()
      sat = sat if sat is not None else random.random()
      val = val if val is not None else random.random()
      to_eightbit = lambda value: int(round(value * 255))
      return map(to_eightbit, colorsys.hsv_to_rgb(hue, sat, val))

    random_color(hue=0)    # something red:  [186, 98, 98]
    random_color(sat=0)    # something grey: [134, 134, 134]
    random_color(sat=1, val=1) # max chroma: [36, 0, 255]


.. figure:: {filename}/images/hexagon-tiling/hexagons_locked_hue.png
    :align: right
    :alt: Randomly brightness and saturation of red hexagons

    :py:`random_color(hue=0)`

    A sample tiling with static hue and variable saturation & brightness.


Random numbers in a restricted range
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We can now generate random colors where not all input wheels are freely spun, but one or more are held down. This way we can match tone or intensity, but depending on the exact input that's locked, it can be a bit boring, or still way too colorful. Exactly one tint of red with only variations in saturation and lightness is boring; getting colors of all hues is too much. What we need is a way to clamp the possible outcomes within a certain range.

The following snippet defines a function that returns functions which can be used to generate our channel values. Providing it with a single number returns a function that always returns that number (the constant option from our previous example). Providing it with a 2-tuple of numbers returns numbers within that range, and providing :py:`None` returns a 'regular' random number generator in the range 0-1:

.. code-block:: python

    def channel_picker(value):
      if value is None:
        return random.random
      if isinstance(value, tuple):
        start, stop = value
        return lambda: random.random() * (stop - start) + start
      return lambda: value

    >>> rand = channel_picker((0.4, 0.6))
    >>> [rand() for _ in range(3)]  #
    [0.4785833631009269, 0.4449304246805125, 0.5504729222480945]
    >>> rand = channel_picker(0.76)
    >>> [rand() for _ in range(3)]  #
    [0.76, 0.76, 0.76]


Piecing it all together
~~~~~~~~~~~~~~~~~~~~~~~

The :py:`channel_picker()` as it's implemented above needs to be adapted to work with our hue values which are in the 0-360 range. It also needs to be connected to the code that constructs the number and then scales it out to fit the 8-bit integer range. With all of these things being very purpose-built, a simple class should do the trick:

.. code-block:: python
    :linenos: table

    import colorsys
    import random

    class HsvColorGenerator(object):
      def __init__(self, hue=None, saturation=None, value=None):
        self.h_func = self._channel_picker(hue, scale=360)
        self.s_func = self._channel_picker(saturation)
        self.v_func = self._channel_picker(value)

      def __call__(self):
        """Returns a random color based on configured functions."""
        hsv = self.h_func(), self.s_func(), self.v_func()
        expander = lambda value: int(round(value * 255))
        return tuple(map(expander, colorsys.hsv_to_rgb(*hsv)))

      def _channel_picker(self, value, scale=1):
        """Returns a function to create (restricted) random values."""
        if value is None:
          return random.random
        scaler = self._scale_input(scale)
        if isinstance(value, tuple):
          start, stop = map(scaler, value)
          return lambda: random.random() * (stop - start) + start
        else:
          value = scaler(value)
          return lambda: value

      def _scale_input(self, scale_max):
        """Creates a function that compresses an range to [0-1]."""
        scale_max = float(scale_max)
        return lambda num: num / scale_max


Footnotes
=========

.. [#raw] blablalba

.. _colorsys: https://docs.python.org/2/library/colorsys.html
