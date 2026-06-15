const categoryCarousel = document.getElementById("categoryCarousel");
const previousCategoryButton = document.querySelector(
    ".category-carousel-prev"
);
const nextCategoryButton = document.querySelector(
    ".category-carousel-next"
);

if (
    categoryCarousel &&
    previousCategoryButton &&
    nextCategoryButton
) {
    let isAnimating = false;

    function getCardDistance() {
        const firstCard = categoryCarousel.querySelector(".category-card");

        if (!firstCard) {
            return 0;
        }

        const trackStyles = window.getComputedStyle(categoryCarousel);
        const gap = parseFloat(trackStyles.columnGap) || 0;

        return firstCard.getBoundingClientRect().width + gap;
    }

    nextCategoryButton.addEventListener("click", () => {
        if (isAnimating) {
            return;
        }

        const firstCard = categoryCarousel.firstElementChild;
        const distance = getCardDistance();

        if (!firstCard || distance === 0) {
            return;
        }

        isAnimating = true;

        categoryCarousel.style.transition = "transform 0.4s ease";
        categoryCarousel.style.transform = `translateX(-${distance}px)`;

        categoryCarousel.addEventListener(
            "transitionend",
            () => {
                categoryCarousel.appendChild(firstCard);

                categoryCarousel.style.transition = "none";
                categoryCarousel.style.transform = "translateX(0)";

                isAnimating = false;
            },
            { once: true }
        );
    });

    previousCategoryButton.addEventListener("click", () => {
        if (isAnimating) {
            return;
        }

        const lastCard = categoryCarousel.lastElementChild;
        const distance = getCardDistance();

        if (!lastCard || distance === 0) {
            return;
        }

        isAnimating = true;

        categoryCarousel.prepend(lastCard);

        categoryCarousel.style.transition = "none";
        categoryCarousel.style.transform = `translateX(-${distance}px)`;

        categoryCarousel.offsetHeight;

        categoryCarousel.style.transition = "transform 0.4s ease";
        categoryCarousel.style.transform = "translateX(0)";

        categoryCarousel.addEventListener(
            "transitionend",
            () => {
                categoryCarousel.style.transition = "none";
                isAnimating = false;
            },
            { once: true }
        );
    });
}