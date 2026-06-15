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

const quantityButtons = document.querySelectorAll(".quantity-button");

quantityButtons.forEach((button) => {
    button.addEventListener("click", async () => {
        const productId = button.dataset.productId;
        const change = Number(button.dataset.change);

        button.disabled = true;

        try {
            const response = await fetch(`/cart/change/${productId}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ change })
            });

            if (!response.ok) {
                throw new Error("Cart update failed.");
            }

            const data = await response.json();

            const quantityElement = document.getElementById(
                `cartQuantity${productId}`
            );

            const lineTotalElement = document.getElementById(
                `cartLineTotal${productId}`
            );

            const cartItem = document.getElementById(
                `sidebarCartItem${productId}`
            );

            if (data.quantity <= 0) {
                cartItem?.remove();
            } else {
                quantityElement.textContent = data.quantity;
                lineTotalElement.textContent =
                    `$${data.line_total.toFixed(2)}`;
            }

            document.getElementById("sidebarCartSubtotal").textContent =
                `$${data.subtotal.toFixed(2)}`;

            document.getElementById("sidebarCartGst").textContent =
                `$${data.gst.toFixed(2)}`;

            document.getElementById("sidebarCartTotal").textContent =
                `$${data.total.toFixed(2)}`;

            const navbarCartCount =
                document.getElementById("navbarCartCount");

            navbarCartCount.textContent = data.cart_count;

            if (data.cart_count === 0) {
                navbarCartCount.classList.add("d-none");
            } else {
                navbarCartCount.classList.remove("d-none");
            }

            if (data.cart_empty) {
                document
                    .getElementById("cartSidebarItems")
                    .classList.add("d-none");

                document
                    .getElementById("emptySidebarCart")
                    .classList.remove("d-none");
            }
        } catch (error) {
            console.error(error);
        } finally {
            button.disabled = false;
        }
    });
});

const postcodeInput = document.getElementById("postcode");
const suburbSelect = document.getElementById("suburb");
const stateInput = document.getElementById("state");
const postcodeStatus = document.getElementById("postcodeStatus");

let postcodeRequestNumber = 0;

async function lookupPostcode() {
    if (
        !postcodeInput ||
        !suburbSelect ||
        !stateInput ||
        !postcodeStatus
    ) {
        return;
    }

    const postcode = postcodeInput.value
        .replace(/\D/g, "")
        .slice(0, 4);

    postcodeInput.value = postcode;

    stateInput.value = "";
    suburbSelect.innerHTML = `
        <option value="">
            Enter your postcode first
        </option>
    `;
    suburbSelect.disabled = true;
    postcodeStatus.textContent = "";
    postcodeStatus.classList.remove(
        "postcode-success",
        "postcode-error"
    );

    if (postcode.length !== 4) {
        return;
    }

    const currentRequestNumber = ++postcodeRequestNumber;

    postcodeStatus.textContent = "Finding suburbs...";

    try {
        const response = await fetch(
            `/api/postcode/${postcode}`
        );

        const data = await response.json();

        if (currentRequestNumber !== postcodeRequestNumber) {
            return;
        }

        if (!response.ok) {
            throw new Error(
                data.error || "Postcode lookup failed."
            );
        }

        stateInput.value = data.state;

        suburbSelect.innerHTML = `
            <option value="">
                Select your suburb
            </option>
        `;

        const previouslySelectedSuburb =
            suburbSelect.dataset.selectedSuburb;

        data.suburbs.forEach((suburb) => {
            const option = document.createElement("option");

            option.value = suburb;
            option.textContent = suburb;

            if (suburb === previouslySelectedSuburb) {
                option.selected = true;
            }

            suburbSelect.appendChild(option);
        });

        suburbSelect.disabled = false;

        postcodeStatus.textContent =
            `${data.suburbs.length} suburb option${
                data.suburbs.length === 1 ? "" : "s"
            } found`;

        postcodeStatus.classList.add(
            "postcode-success"
        );
    } catch (error) {
        stateInput.value = "";

        suburbSelect.innerHTML = `
            <option value="">
                No suburbs available
            </option>
        `;

        suburbSelect.disabled = true;

        postcodeStatus.textContent = error.message;
        postcodeStatus.classList.add(
            "postcode-error"
        );
    }
}

if (postcodeInput) {
    postcodeInput.addEventListener(
        "input",
        lookupPostcode
    );

    if (postcodeInput.value.length === 4) {
        lookupPostcode();
    }
}

const savedCheckoutDetails =
    document.getElementById("savedCheckoutDetails");

const checkoutDetailsFields =
    document.getElementById("checkoutDetailsFields");

const editCheckoutDetailsButton =
    document.getElementById("editCheckoutDetailsButton");

const cancelCheckoutEditButton =
    document.getElementById("cancelCheckoutEditButton");

if (
    savedCheckoutDetails &&
    checkoutDetailsFields &&
    editCheckoutDetailsButton
) {
    editCheckoutDetailsButton.addEventListener("click", () => {
        savedCheckoutDetails.classList.add("d-none");
        checkoutDetailsFields.classList.remove("d-none");
    });
}

if (
    savedCheckoutDetails &&
    checkoutDetailsFields &&
    cancelCheckoutEditButton
) {
    cancelCheckoutEditButton.addEventListener("click", () => {
        checkoutDetailsFields.classList.add("d-none");
        savedCheckoutDetails.classList.remove("d-none");
    });
}

const profileDetailsSummary =
    document.getElementById("profileDetailsSummary");

const accountProfileForm =
    document.getElementById("accountProfileForm");

const editProfileButton =
    document.getElementById("editProfileButton");

const cancelProfileEditButton =
    document.getElementById("cancelProfileEditButton");

if (
    profileDetailsSummary &&
    accountProfileForm &&
    editProfileButton
) {
    editProfileButton.addEventListener("click", () => {
        profileDetailsSummary.classList.add("d-none");
        accountProfileForm.classList.remove("d-none");
    });
}

if (
    profileDetailsSummary &&
    accountProfileForm &&
    cancelProfileEditButton
) {
    cancelProfileEditButton.addEventListener("click", () => {
        accountProfileForm.classList.add("d-none");
        profileDetailsSummary.classList.remove("d-none");
    });
}

const otpForm = document.getElementById("otpVerificationForm");
const otpBoxes = document.querySelectorAll(".otp-box");
const otpHiddenInput = document.getElementById("otp");

if (otpForm && otpBoxes.length === 4 && otpHiddenInput) {
    otpBoxes.forEach((box, index) => {
        box.addEventListener("input", () => {
            box.value = box.value.replace(/\D/g, "").slice(0, 1);

            if (box.value && index < otpBoxes.length - 1) {
                otpBoxes[index + 1].focus();
            }

            otpHiddenInput.value = Array.from(otpBoxes)
                .map((input) => input.value)
                .join("");
        });

        box.addEventListener("keydown", (event) => {
            if (
                event.key === "Backspace" &&
                !box.value &&
                index > 0
            ) {
                otpBoxes[index - 1].focus();
            }
        });

        box.addEventListener("paste", (event) => {
            const pastedValue = event.clipboardData
                .getData("text")
                .replace(/\D/g, "")
                .slice(0, 4);

            if (!pastedValue) {
                return;
            }

            event.preventDefault();

            pastedValue.split("").forEach((digit, digitIndex) => {
                if (otpBoxes[digitIndex]) {
                    otpBoxes[digitIndex].value = digit;
                }
            });

            otpHiddenInput.value = pastedValue;

            const focusIndex = Math.min(
                pastedValue.length,
                otpBoxes.length
            ) - 1;

            otpBoxes[focusIndex].focus();
        });
    });

    otpForm.addEventListener("submit", (event) => {
        const otp = Array.from(otpBoxes)
            .map((input) => input.value)
            .join("");

        otpHiddenInput.value = otp;

        if (otp.length !== 4) {
            event.preventDefault();
            otpBoxes[0].focus();
        }
    });
}

const themeToggleButton =
    document.getElementById("themeToggleButton");

const themeToggleIcon =
    document.getElementById("themeToggleIcon");

function updateThemeIcon(theme) {
    if (!themeToggleIcon) {
        return;
    }

    themeToggleIcon.textContent =
        theme === "dark" ? "☀" : "☾";
}

const currentTheme =
    document.documentElement.dataset.theme || "light";

updateThemeIcon(currentTheme);

if (themeToggleButton) {
    themeToggleButton.addEventListener("click", () => {
        const activeTheme =
            document.documentElement.dataset.theme;

        const newTheme =
            activeTheme === "dark" ? "light" : "dark";

        document.documentElement.dataset.theme =
            newTheme;

        localStorage.setItem(
            "veroTheme",
            newTheme
        );

        updateThemeIcon(newTheme);
    });
}