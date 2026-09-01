html
    head
    body
        .page.cover.large-margin
            img.background_photo.absolute_wrapper -> cover
            .absolute_wrapper
                img.logo -> logo
                h1 -> "{title} {$year}"
                h2 -> "Planer malarski coroczny w ustce"

        .page.empty

        -> $page_num.restart()

        .page
            h2.list_header -> "Uczestnicy pleneru {title} {$year}"
            .list_container
                ul.artists_list -> artists.sort_by(last_name, first_name).each() as artist
                    li
                        span.names -> "{artist.first_name} {artist.last_name}"
                        span.town -> artist.town
            img.background_photo.absolute_wrapper -> group_photo

        .page.large-margin
            h2.subheading -> "Słów kilka tytułem wstępu"
            
            p.base-text -> "Sztuka od wieków splata się z potęgą żywiołów, a morze – w swojej nieprzewidywalności i bezkresie – pozostaje jednym z najbardziej fascynujących motywów. Niniejszy katalog to zapis niezwykłego spotkania twórców, którzy podczas pleneru "M jak Morze" podjęli próbę uchwycenia ulotnych chwil nadbałtyckiego krajobrazu. Na kartach tego wydawnictwa znajdą Państwo różnorodne interpretacje nadmorskiej przestrzeni, od chłodnej, melancholijnej abstrakcji po pulsujący feerią barw impresjonizm. Każdy z zaprezentowanych tu artystów przemawia własnym, unikalnym językiem wizualnym, wchodząc w intymny dialog z otaczającą naturą. Zapraszamy do zanurzenia się w tę wyjątkową opowieść, w której wiatr, piasek i fale stają się pretekstem do głębszej refleksji nad pięknem otaczającego nas świata."
            
            .page-footer
                    span.info -> "{title} {$year}"
                    span.num -> $page_num
            
        -> artists.sort_by(last_name, first_name).chunk(1) as group
            .page
                .artists-grid -> group.each() as artist
                    @artist -> artist
                .page-footer
                    span.info -> "{title} {$year}"
                    span.num -> $page_num