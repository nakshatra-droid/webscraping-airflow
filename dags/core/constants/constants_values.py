class AmazonConstants:
    CATEGORY_URL = (
        "https://www.amazon.in/s?i=computers"
        "&rh=n%3A1375424031&s=popularity-rank&fs=true&ref=lp_1375424031_sar"
    )

    NUMBER_OF_URLS = 10
    BATCH_SIZE = 5
    BASE_URL = "https://www.amazon.in"
    SOURCE = "AMAZON"

    # Single product URL (kept for standalone testing)
    SINGLE_URL = "https://www.amazon.in/dp/B0FM38SKN8?th=1"

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    MAIN_PAGE_SEL="div.s-main-slot"
    ACTIVE_SEL="div.s-main-slot a[href*='/dp/'], div.s-main-slot a[href*='/gp/product/']"
    # CSS selector for product card links
    CARD_LINK_SEL = "a.a-link-normal.s-line-clamp-4.a-text-normal"

    # Next page button
    NEXT_BTN_SEL = "a[aria-label^='Go to next page'], .s-pagination-next"

    PRODUCT_TITLE_SEL = "#productTitle"
    ASIN_SEL = "input#ASIN"
    BRAND_SEL = "#bylineInfo"
    PRICE_WHOLE_SEL = ".a-price-whole"
    PRICE_FRAC_SEL = ".a-price-fraction"
    PRICE_SEL = "#priceblock_ourprice, #priceblock_dealprice"
    MRP_SEL = ".a-price.a-text-price .a-offscreen"
    DISCOUNT_SEL = ".savingsPercentage, #dealprice_savings .a-color-price"
    RATING_SEL = "[data-hook='rating-out-of-text']"
    RATING_FIRST_SEL = ".a-icon-star .a-icon-alt"
    REVIEW_SEL = "[data-hook='total-review-count']"
    REVIEW_FIRST_SEL = "#acrCustomerReviewText"
    AVAILABILITY_SEL = "#availability span"
    SOLD_BY_SEL = "#sellerProfileTriggerId"
    SHIPS_FROM_SEL = "#shipsFromSoldBy_feature_div .tabular-buybox-text"
    MAIN_SRC_IMG_SEL = "#landingImage"
    THUMBNAILS_SEL = "#altImages .item img"
    FEATURES_SEL = "#feature-bullets ul li span.a-list-item"
    TECH_SPEC_SECTION1 = "#productDetails_techSpec_section_1"
    TECH_SPEC_SECTION2 = "#productDetails_techSpec_section_2"
    PRODUCT_DETAILS_SECTION1 = "#productDetails_detailBullets_sections1"
    PRODUCT_DETAIL_TABLE = "table.prodDetTable"
    TECHNICAL_SPEC_SECTION = "#technicalSpecifications_section_1"
    ITEMS = "#detailBullets_feature_div li"
    PRODUCT_DESCRIPTION = "#productDescription"
    VARIANTS = ".a-button-selected .a-button-text"


class FlipkartConstants:
    CATEGORY_URL = (
        "https://www.flipkart.com/laptops/pr?sid=6bo,b5g&otracker=categorytree"
    )
    NUMBER_OF_URLS = 10
    BATCH_SIZE = 5
    BASE_URL = "https://www.flipkart.com"
    SOURCE = "FLIPKART"

    PRICE_SEL = '._1psv1zeb9[font="default-fk-font-m"]'
    DISCOUNT_SEL = '[font="default-fk-font-m"]'
    RATING_SEL = '.css-146c3p1[style*="inter_bold"][style*="margin-right:2px"]'
    REVIEW_SEL = '.css-146c3p1[style*="inter_regular"][style*="margin-left:2px"]'
    IMAGE_SEL = 'img[src*="rukminim2.flixcart.com/image/"]'
    SPEC_TAB_SEL = (
        '[font="default-fk-font-m"]:has-text("Specifications"), '
        '[font="default-fk-font-m"]:has-text("All Details")'
    )
    SPEC_ACTIVE_SEL = "._7dzyg2m"
    SPEC_GRID_SEL = ".grid-formation-dynamic"
    SEE_MORE_SEL = '[text="See more"]'
    SPEC_ITEMS_SEL = ".grid-formation-dynamic"
    SPEC_ITEM_KEY_SEL = ".v1zwn27"
    SPEC_ITEM_VALUE_SEL = '.v1zwn26[font="s"]'


class ActivityTypes:
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    REDIRECTED = "REDIRECTED"
    ALREADY_EXIST = "ALREADY_EXIST"
    FIELD_MISSING = "FIELD_MISSING"
