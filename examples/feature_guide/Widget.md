# Widget

## Section #1

### SubSection

#### SubSubSection

##### Paragraph

###### SubParagraph

Lorem ipsum *dolor* sit _amet_. consectetur adipiscing elit. Duis sed nunc et dolor aliquam ultricies. Proin vitae urna mollis, viverra nibh quis, sollicitudin ipsum. Duis tempus molestie erat, eu placerat felis ullamcorper vel. Proin congue risus id congue aliquam. Praesent ac condimentum leo. In interdum augue eget malesuada euismod. Morbi sodales volutpat massa, quis tempus tortor blandit ac. Curabitur aliquet tortor ac lectus luctus lacinia sed sit amet eros. Fusce metus libero, convallis at feugiat tempus, vehicula id mi. Fusce semper magna quis tellus iaculis ornare. Nam gravida est quis mauris porta semper. Suspendisse imperdiet massa sed mattis egestas. Sed hendrerit, tellus eget posuere placerat, leo sapien imperdiet turpis, sit amet rhoncus turpis felis interdum ligula. Curabitur luctus purus erat, nec ultricies nunc dignissim in.

```mermaid
graph
	widget --> lw[left widgeting]
	widget --> rw[right widgeting]
```

- This is a list
- with 2_items
    - with 2_items

![[Widgeting]]

```typst
#import "@preview/cetz:0.1.2"

#cetz.canvas({
  import cetz.draw: *

  let chart(..values, name: none) = {
    let values = values.pos()

    let offset = 0
    let total = values.fold(0, (s, v) => s + v.at(0))

    let segment(from, to) = {
      merge-path(close: true, {
        line((0, 0), (rel: (360deg * from, 1)))
        arc((), start: from * 360deg, stop: to * 360deg, radius: 1)
      })
    }

    group(name: name, {
      stroke((paint: black, join: "round"))

      let i = 0
      for v in values {
        fill(v.at(1))
        let value = v.at(0) / total

        // Draw the segment
        segment(offset, offset + value)

        // Place an anchor for each segment
        anchor(v.at(2), (offset * 360deg + value * 180deg, .75))

        offset += value
      }
    })
  }

  // Draw the chart
  chart((10, red, "red"),
        (3, blue, "blue"),
        (1, green, "green"),
        name: "chart")

  set-style(mark: (fill: white, start: "o", stroke: black),
            content: (padding: .1))

  // Draw annotations
  line("chart.red", ((), "-|", (2, 0)))
  content((), [Red], anchor: "left")

  line("chart.blue", (1, -1), ((), "-|", (2,0)))
  content((), [Blue], anchor: "left")

  line("chart.green", ((), "-|", (2,0)))
  content((), [Green], anchor: "left")
})
```
