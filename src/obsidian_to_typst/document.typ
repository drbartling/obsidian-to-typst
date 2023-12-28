#set document(title:[TheTitleOfTheDocument], date:auto)
#let title = "TheTitleOfTheDocument"
#let doc_date = datetime.today().display()

#set page(
    header: align(
        right + horizon,
        title
    ),
)

#let fit(body) = {
    layout(container_size => {
        style(styles => {
            let body_size = measure(body, styles)

            let width_ratio = (container_size.width / body_size.width) * 100%
            let height_ratio = (container_size.height / body_size.height) * 100%
            let max_ratio = 100%
            let fit_ratio = calc.min(width_ratio, height_ratio, max_ratio)
            scale(x:fit_ratio, y: fit_ratio, origin: bottom + left)[#body]
        })
    })
}

#show link: underline

#align(center, text(17pt)[
    *#title*
])
#align(center, [
    #doc_date
])
#outline(depth:1)
// #show: rest => columns(2, rest)
#set heading(numbering:"1.")
