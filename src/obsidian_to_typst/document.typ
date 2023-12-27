#set document(title:[TheTitleOfTheDocument], date:auto)

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
#outline(depth:1)
#set heading(numbering:"1.")
