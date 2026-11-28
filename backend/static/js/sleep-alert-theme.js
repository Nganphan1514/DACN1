(function () {
    "use strict";
    if (!window.tailwind) return;

    const accent = {
        100: "#E4F0E1", 200: "#CEE2CB", 300: "#B9D4B7", 400: "#A4C3A2",
        500: "#92B992", 600: "#456458", 700: "#354F44", 800: "#293E35", 900: "#1C2E26"
    };
    window.tailwind.config = {
        theme: {
            extend: {
                colors: {
                    slate: {
                        100: "#EAF3E8", 200: "#DAE7DC", 300: "#CADDD0", 400: "#A9BDB2",
                        500: "#8EA89A", 600: "#698779", 700: "#48685A", 800: "#2C443A",
                        900: "#1C2E26", 950: "#14211B"
                    },
                    blue: accent,
                    cyan: accent,
                    sky: accent
                }
            }
        }
    };
})();
