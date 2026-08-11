import os
import json
import urllib.request
from datetime import datetime
from collections import defaultdict
from xml.sax.saxutils import escape

USERNAME = "ayoubgouiaa"
TOKEN = os.environ["GH_TOKEN"]

OUTPUT = "assets/github-activity.svg"

WIDTH = 1000
HEIGHT = 360

LEFT = 65
RIGHT = 30
TOP = 55
BOTTOM = 65

GRAPH_WIDTH = WIDTH - LEFT - RIGHT
GRAPH_HEIGHT = HEIGHT - TOP - BOTTOM

BG = "#0D1117"
BLUE = "#58A6FF"
TEXT = "#8B949E"
GRID = "#21262D"


# ---------------------------------------------------------
# Get GitHub contribution data
# ---------------------------------------------------------

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": query,
    "variables": {
        "login": USERNAME
    }
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-activity-graph"
    },
    method="POST"
)

with urllib.request.urlopen(request) as response:
    data = json.loads(response.read().decode("utf-8"))


if "errors" in data:
    raise Exception(data["errors"])


calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


# ---------------------------------------------------------
# Aggregate daily contributions → monthly contributions
# ---------------------------------------------------------

monthly = defaultdict(int)

for week in calendar["weeks"]:
    for day in week["contributionDays"]:

        date = datetime.strptime(
            day["date"],
            "%Y-%m-%d"
        )

        month_key = date.strftime("%Y-%m")

        monthly[month_key] += day["contributionCount"]


# ---------------------------------------------------------
# Get last 12 months
# ---------------------------------------------------------

today = datetime.today()

months = []

year = today.year
month = today.month

for _ in range(12):

    key = f"{year:04d}-{month:02d}"

    label = datetime(
        year,
        month,
        1
    ).strftime("%b")

    months.insert(
        0,
        {
            "key": key,
            "label": label,
            "year": year,
            "value": monthly.get(key, 0)
        }
    )

    month -= 1

    if month == 0:
        month = 12
        year -= 1


# ---------------------------------------------------------
# Calculate graph points
# ---------------------------------------------------------

max_value = max(
    month["value"]
    for month in months
)

if max_value == 0:
    max_value = 1


points = []

for index, month_data in enumerate(months):

    x = LEFT + (
        index *
        GRAPH_WIDTH /
        (len(months) - 1)
    )

    y = TOP + GRAPH_HEIGHT - (
        month_data["value"] /
        max_value *
        GRAPH_HEIGHT
    )

    points.append((x, y))


# ---------------------------------------------------------
# Create smooth curve
# ---------------------------------------------------------

curve = f"M {points[0][0]:.2f} {points[0][1]:.2f}"

for i in range(1, len(points)):

    previous_x, previous_y = points[i - 1]
    current_x, current_y = points[i]

    midpoint = (
        previous_x + current_x
    ) / 2

    curve += (
        f" C "
        f"{midpoint:.2f} {previous_y:.2f}, "
        f"{midpoint:.2f} {current_y:.2f}, "
        f"{current_x:.2f} {current_y:.2f}"
    )


baseline = TOP + GRAPH_HEIGHT

area = (
    curve
    + f" L {points[-1][0]:.2f} {baseline}"
    + f" L {points[0][0]:.2f} {baseline}"
    + " Z"
)


# ---------------------------------------------------------
# Build SVG
# ---------------------------------------------------------

svg = f"""<svg
xmlns="http://www.w3.org/2000/svg"
width="{WIDTH}"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}">

<defs>

<linearGradient
id="gradient"
x1="0"
y1="0"
x2="0"
y2="1">

<stop
offset="0%"
stop-color="{BLUE}"
stop-opacity="0.35"/>

<stop
offset="100%"
stop-color="{BLUE}"
stop-opacity="0"/>

</linearGradient>

</defs>

<rect
width="100%"
height="100%"
rx="18"
fill="{BG}"/>

<!-- Title -->

<text
x="{LEFT}"
y="30"
fill="{BLUE}"
font-family="Arial, sans-serif"
font-size="18"
font-weight="700">

GitHub Activity — Last 12 Months

</text>
"""


# ---------------------------------------------------------
# Horizontal grid lines
# ---------------------------------------------------------

for i in range(5):

    y = TOP + (
        i *
        GRAPH_HEIGHT /
        4
    )

    value = round(
        max_value -
        i * max_value / 4
    )

    svg += f"""

<line
x1="{LEFT}"
y1="{y:.2f}"
x2="{WIDTH - RIGHT}"
y2="{y:.2f}"
stroke="{GRID}"
stroke-width="1"/>

<text
x="{LEFT - 10}"
y="{y + 4:.2f}"
text-anchor="end"
fill="{TEXT}"
font-family="Arial, sans-serif"
font-size="11">

{value}

</text>
"""


# ---------------------------------------------------------
# Area under curve
# ---------------------------------------------------------

svg += f"""

<path
d="{area}"
fill="url(#gradient)"/>

<path
d="{curve}"
fill="none"
stroke="{BLUE}"
stroke-width="4"
stroke-linecap="round"
stroke-linejoin="round"/>
"""


# ---------------------------------------------------------
# Monthly points + labels
# ---------------------------------------------------------

for point, month_data in zip(points, months):

    x, y = point

    svg += f"""

<circle
cx="{x:.2f}"
cy="{y:.2f}"
r="5"
fill="{BG}"
stroke="{BLUE}"
stroke-width="3"/>

<text
x="{x:.2f}"
y="{y - 13:.2f}"
text-anchor="middle"
fill="{BLUE}"
font-family="Arial, sans-serif"
font-size="11"
font-weight="600">

{month_data["value"]}

</text>

<text
x="{x:.2f}"
y="{baseline + 28:.2f}"
text-anchor="middle"
fill="{TEXT}"
font-family="Arial, sans-serif"
font-size="12">

{escape(month_data["label"])}

</text>
"""


svg += """

</svg>
"""


# ---------------------------------------------------------
# Save SVG
# ---------------------------------------------------------

os.makedirs(
    "assets",
    exist_ok=True
)

with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as file:

    file.write(svg)


print("Monthly GitHub activity graph generated!")

for month_data in months:

    print(
        f'{month_data["label"]}: '
        f'{month_data["value"]}'
    )
