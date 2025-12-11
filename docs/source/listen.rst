APRSD listen
============

Running the APRSD listen command
---------------------------------

The ``aprsd listen`` command allows you to listen to packets on the APRS-IS Network based on a FILTER.
This is useful for monitoring specific APRS traffic without running the full server.

Once APRSD is :doc:`installed <install>` and :doc:`configured <configure>`, the listen command can be started by running:

.. code-block:: shell

   aprsd listen [FILTER]

The FILTER parameter is optional and follows the APRS-IS filter format. For example, ``m/300`` filters for
messages within 300 miles of your configured location.

Example usage
-------------

.. code-block:: text

    ❯ aprsd listen m/300
    2025-12-11 09:44:33.349 | Python version: 3.14.0rc1 free-threading build (main, Aug  8 2025, 16:53:07) [Clang 20.1.4 ]
    2025-12-11 09:44:33.349 | APRSD Listen Started version: 4.2.5.dev17+g0ef131678.d20251211
    2025-12-11 09:44:33.365 | Creating aprslib client(155.138.131.1:14580) and logging in WB4BOR-1. try #1
    2025-12-11 09:44:33.365 | Attempting connection to 155.138.131.1:14580
    2025-12-11 09:44:33.391 | Connected to ('155.138.131.1', 14580)
    2025-12-11 09:44:33.469 | Login successful
    2025-12-11 09:44:33.469 | Connected to T2CAEAST
    2025-12-11 09:44:33.469 | Creating client connection
    2025-12-11 09:44:33.469 | <aprsd.client.client.APRSDClient object at 0x57a5c7bc310>
    2025-12-11 09:44:33.469 | Setting filter to: ('m/300',)
    2025-12-11 09:44:33.469 | No packet filtering enabled.
    2025-12-11 09:44:33.469 | Not Loading any plugins use --load-plugins to load what's defined in the config file.
    2025-12-11 09:44:35.458 | RX(1)↓ BeaconPacket:None KQ4INX-D →TCPIP*→qAC→KQ4INX-DS→ APDG03 : Lat:37.598 Lon:-77.323 70cm MMDVM Voice (DMR) 440.52500MHz +5.0000MHz, APRS for DMRGateway  : East-Northeast@85.57miles
    2025-12-11 09:44:35.472 | RX(2)↓ StatusPacket:None KQ4INX-D →qAS→KQ4INX→ APDG03 : Powered by WPSD (https://wpsd.radio)
    2025-12-11 09:44:36.599 | RX(3)↓ BeaconPacket:None WX4EMC-1 →qAR→W4KEL-12→ ID : Lat:0.000 Lon:0.000 None  : East@5607.38miles
    2025-12-11 09:44:38.306 | RX(4)↓ BeaconPacket:None KC4JGC-10 →TCPIP*→qAC→T2BIO→ APDR16 : Lat:38.043 Lon:-78.722   : North@48.78miles
    2025-12-11 09:44:39.472 | RX(5)↓ WeatherPacket:None K9MJM-1 →TCPIP*→qAC→T2SYDNEY→ SKY : Temp -04F Humidity 92% Wind 000MPH@96 Pressure 1013.3mb Rain 0.0in/24hr  : West-Southwest@175.80miles
    2025-12-11 09:44:39.524 | RX(6)↓ BeaconPacket:None KA6LOW →TCPIP*→qAC→T2RDU→ APDPRS : Lat:39.126 Lon:-77.574   : North-Northeast@141.21miles
    2025-12-11 09:44:41.392 | RX(7)↓ MicEPacket:None KM4HFB-9 →WIDE1-1→WIDE2-1→qAR→W4KEL-12→ SX1U5Y : Lat:38.260 Lon:-77.550 Altitude 078 Speed 015MPH Course 248 110 mbits  : Northeast@95.08miles
    2025-12-11 09:44:41.418 | RX(8)↓ BeaconPacket:None K8WVU-9 →W8SP-1→WIDE1*→WIDE2-1→qAR→KF8LO-1→ APAT81 : Lat:39.580 Lon:-79.957 using Radioddity DB25-D  : North-Northwest@165.67miles
    2025-12-11 09:44:42.131 | RX(9)↓ MicEPacket:None N0OEP-9 →WIDE1-1→WIDE2-1→qAR→KB4ZIN-1→ S7QW6Y : Lat:37.295 Lon:-76.716 Altitude 028 Course 063 101 mbits  : East@117.30miles
    2025-12-11 09:44:42.723 | RX(10)↓ ObjectPacket:None KJ4ACB-S →TCPIP*→qAC→KJ4ACB-GS→ APDG01 : Lat:35.444 Lon:-78.515 Altitude 003 RNG 002 70cm Voice (D-Star) 434.60000MHz +0.0000MHz  : South@132.62miles
    2025-12-11 09:44:43.158 | RX(11)↓ WeatherPacket:None KO4FR →TCPIP*→qAC→T2SPAIN→ APRS : Temp 005F Humidity 54% Wind 000MPH@146 Pressure 1011.9mb Rain 0.09in/24hr  : Southeast@45.96miles
    2025-12-11 09:44:43.249 | RX(12)↓ BeaconPacket:None AA4HI-4 →TCPIP*→qAS→N4UED-4→ APMI06 : Lat:36.449 Lon:-77.636 WX3in1Plus2.0 U=12.5V,T=??.?C/??.?F  : Southeast@91.24miles

The listen command connects to the APRS-IS network and displays packets matching the specified filter.
In the example above, packets within 300 miles are displayed, showing various packet types including MicEPacket,
BeaconPacket, and WeatherPacket.

APRS-IS Filter Syntax
----------------------

The ``aprsd listen`` command supports the full APRS-IS server-side filter syntax. For complete documentation
on all available filter types and options, see the `APRS-IS Filter Documentation <http://www.aprs-is.net/javAPRSFilter.aspx>`_.

Filters allow you to subscribe to specific APRS traffic based on various criteria. Multiple filter specifications
can be combined, separated by spaces. If any filter matches, the packet is passed.

You can also exclude packets by prefixing a filter parameter with a hyphen (-). This tells the filter to
approve packets that match the include filters **except** those that match the exclude filters.

For example, to get all stations within 200 km except stations with the prefix "CW":

.. code-block:: shell

   aprsd listen m/200 -p/CW

The following filter types are available:

Range Filter (r/lat/lon/dist)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes position packets and objects within ``dist`` km from the specified latitude/longitude.
Latitude and longitude are signed decimal degrees (negative for West/South, positive for East/North).

Up to 9 range filters can be defined simultaneously for better coverage. Messages addressed to stations
within the range are also passed.

**Example:**

.. code-block:: shell

   aprsd listen r/33/-97/200

This filters for packets within 200 km of latitude 33, longitude -97 (Dallas, Texas area).

My Range Filter (m/dist)
~~~~~~~~~~~~~~~~~~~~~~~~

Same as the range filter, except the center is defined as the last known position of the logged-in client
(as configured in your APRSD config file).

**Example:**

.. code-block:: shell

   aprsd listen m/300

This filters for packets within 300 miles of your configured location.

Friend Range Filter (f/call/dist)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Same as the range filter, except the center is defined as the last known position of the specified callsign.
Up to 9 friend filters can be defined simultaneously.

**Example:**

.. code-block:: shell

   aprsd listen f/WB4BOR-1/50

This filters for packets within 50 km of the last known position of WB4BOR-1.

Area Filter (a/latN/lonW/latS/lonE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Works like the range filter but defines a rectangular box of coordinates. Coordinates can be seen as
upper-left and lower-right corners. Latitude/longitude are decimal degrees (South and West are negative).
Up to 9 area filters can be defined simultaneously.

**Example:**

.. code-block:: shell

   aprsd listen a/40/-80/35/-75

This filters for packets in a box from latitude 40N, longitude 80W to latitude 35N, longitude 75W.

Prefix Filter (p/aa/bb/cc...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes traffic with fromCall that starts with any of the specified prefixes.

**Example:**

.. code-block:: shell

   aprsd listen p/WB4/KM6

This filters for packets from callsigns starting with "WB4" or "KM6".

Budlist Filter (b/call1/call2...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all traffic from exact callsigns: call1, call2, etc. The asterisk (*) wildcard is allowed.

**Example:**

.. code-block:: shell

   aprsd listen b/WB4BOR-1/KM6LYW

This filters for packets from exactly WB4BOR-1 or KM6LYW.

Object Filter (o/obj1/obj2...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all objects with the exact name of obj1, obj2, etc. The asterisk (*) wildcard is allowed.
Spaces are not allowed. Use ``|`` for ``/`` and ``~`` for ``*`` in object names.

**Example:**

.. code-block:: shell

   aprsd listen o/APRS*/WEATHER

This filters for objects named "APRS*" or "WEATHER".

Strict Object Filter (os/obj1/obj2...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all objects with the exact name of obj1, obj2, etc. Objects are always 9 characters and Items
are 3 to 9 characters. There can only be one ``os`` filter and it must be at the end of the filter line.
The asterisk (*) wildcard is allowed. Use ``|`` for ``/`` and ``~`` for ``*`` in object names.

Type Filter (t/poimqstunw or t/poimqstuw/call/km)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all traffic based on packet type. One or more types can be defined:

- ``p`` = Position packets
- ``o`` = Objects
- ``i`` = Items
- ``m`` = Message
- ``q`` = Query
- ``s`` = Status
- ``t`` = Telemetry
- ``u`` = User-defined
- ``n`` = NWS format messages and objects
- ``w`` = Weather

The weather type filter also passes position packets for positionless weather packets.

The second format allows putting a radius limit around a callsign (station callsign-SSID or object name)
for the requested station types.

**Examples:**

.. code-block:: shell

   aprsd listen t/mw
   aprsd listen t/poimqstuw/WB4BOR-1/50

The first example filters for messages and weather packets. The second filters for all packet types
within 50 km of WB4BOR-1.

Symbol Filter (s/pri/alt/over)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filters by symbol. ``pri`` = symbols in primary table, ``alt`` = symbols in alternate table,
``over`` = overlay character (case sensitive). Use ``|`` for ``/`` in symbol specifications.

**Examples:**

.. code-block:: shell

   aprsd listen s/->
   aprsd listen s//#
   aprsd listen s//#/T

The first passes all House and Car symbols (primary table). The second passes all Digi with or without
overlay. The third passes all Digi with overlay of capital "T".

Digipeater Filter (d/digi1/digi2...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all packets that have been digipeated by a particular station(s) (the station's call is in the path).
The asterisk (*) wildcard is allowed.

**Example:**

.. code-block:: shell

   aprsd listen d/WIDE1-1/WIDE2-1

This filters for packets digipeated by WIDE1-1 or WIDE2-1.

Entry Station Filter (e/call1/call2/...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all packets with the specified callsign-SSID(s) immediately following the q construct. This allows
filtering based on receiving IGate, etc. Supports asterisk (*) wildcard.

**Example:**

.. code-block:: shell

   aprsd listen e/T2CAEAST/T2SYDNEY

This filters for packets received by T2CAEAST or T2SYDNEY IGates.

Group Message Filter (g/call1/call2/...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all message packets with the specified callsign-SSID(s) as the addressee of the message.
Supports asterisk (*) wildcard.

**Example:**

.. code-block:: shell

   aprsd listen g/REPEAT/APRS

This filters for messages addressed to REPEAT or APRS.

Unproto Filter (u/unproto1/unproto2/...)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passes all packets with the specified destination callsign-SSID(s) (also known as the To call or unproto call).
Supports asterisk (*) wildcard.

**Example:**

.. code-block:: shell

   aprsd listen u/APRS*/CQ

This filters for packets with destination callsigns starting with "APRS" or "CQ".

q Construct Filter (q/con/I)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filters by q Construct command. ``con`` = list of q Constructs to pass (case sensitive),
``I`` = Pass positions from IGATES identified by qAr, qAo, or qAR.

**Examples:**

.. code-block:: shell

   aprsd listen q/C
   aprsd listen q/rR
   aprsd listen q//I

The first passes all traffic with qAC. The second passes all traffic with qAr or qAR.
The third passes all position packets from IGATES identified in other packets by qAr or qAR.

Filter Notes
~~~~~~~~~~~~

- Multiple filter definitions can be combined, separated by spaces
- If any filter matches, the packet is passed (OR logic)
- Exclude filters (prefixed with ``-``) block specified packets from include filters
- Standard port functionality such as messaging for IGates is not affected
- Filters only affect data going to the client; packets from the client or gated by the client are not filtered
- The filter command can be set as part of the login line or as a separate command
- Use ``filter default`` to reset to the predefined filter for that port

For more information, see the `APRS-IS Filter Documentation <http://www.aprs-is.net/javAPRSFilter.aspx>`_.

Key differences from the server command
----------------------------------------

Unlike the ``aprsd server`` command, the listen command:

- Does not load plugins by default (use ``--load-plugins`` to enable them)
- Does not respond to messages
- Is designed for monitoring and logging APRS traffic
- Supports APRS-IS filter syntax for targeted packet monitoring

.. include:: links.rst
