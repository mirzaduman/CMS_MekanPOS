let categories = document.querySelectorAll('.category')
let minus = document.querySelector('.product-order-amount .minus')
let plus = document.querySelector('.product-order-amount .plus')
let shownAmount = document.querySelector('.product-order-amount .shown-amount')
let hiddenAmount = document.querySelector('.product-order-amount .hidden-amount')
let checkbox = document.querySelectorAll('.extra-checkbox')
let endPrice = document.querySelector('.price-value')


function closeModal(element) {
    let prompt  = element.parentNode.parentNode.parentNode.parentNode.querySelector('.delete-order-prompt')
    prompt.classList.remove('active')
}


function gangToggle(element) {
    document.querySelectorAll('.gang-name').forEach((gang) => {
        gang.classList.remove('active')
    })
    element.parentNode.querySelector('.gang-name').classList.add('active')
}


if (checkbox) {
    checkbox.forEach((element) => {
        element.addEventListener('click', () => {
            let amount = parseInt(shownAmount.innerText)
            let extraPrice = element.parentNode.querySelector('.extra-price-value').innerHTML
            element.querySelector('.unchecked').classList.toggle('active')
            if (element.querySelector('.checkbox-input').checked == true) {
                element.querySelector('.checkbox-input').checked = false
                endPrice.innerText = parseFloat(parseFloat(endPrice.innerText) - (parseFloat(extraPrice ) * amount)).toFixed(2)
            } else if (element.querySelector('.checkbox-input').checked == false) {
                element.querySelector('.checkbox-input').checked = true
                endPrice.innerText = parseFloat(parseFloat(endPrice.innerText) + (parseFloat(extraPrice ) * amount)).toFixed(2)
            }
            element.querySelector('.checked').classList.toggle('active')
        })
    })
}


if (categories) {
    function categoryChanger(element) {
        categories.forEach((category) => {
                category.classList.remove('active')
            }
        )
        element.classList.add('active')
    }
}

if (minus) {
    function decreaseAmount() {
        let amount = parseFloat(shownAmount.innerText)
        if (amount > 1) {
            let new_value = (parseInt(shownAmount.innerText) - 1).toString()
            shownAmount.innerText = new_value
            hiddenAmount.value = new_value
            endPrice.innerText = parseFloat(parseFloat(endPrice.innerText).toFixed(2) - (parseFloat(endPrice.innerText).toFixed(2) / amount)).toFixed(2)
        }
    }
    minus.addEventListener('click', decreaseAmount)
}

if (plus) {
    function increaseAmount() {
        let amount = parseInt(shownAmount.innerText)
        let new_value = (amount + 1).toString()
        shownAmount.innerText = new_value
        hiddenAmount.value = new_value
        endPrice.innerText = parseFloat(parseFloat(endPrice.innerText) + parseFloat(parseFloat(endPrice.innerText) / amount)).toFixed(2)
    }

    plus.addEventListener('click', increaseAmount)
}
