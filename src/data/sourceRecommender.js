/**
 * Indian & Global Product-to-Source Recommendation Engine
 * Analyzes product name & domain to select optimal review sources.
 */

export const SOURCE_MATRIX = {
  fintech: {
    categoryName: "Fintech & Stock Trading",
    icon: "Landmark",
    bestSources: [
      { name: "Moneycontrol", url: "https://moneycontrol.com", relevance: "98%", rationale: "Premier Indian financial media & active retail investor forums." },
      { name: "MouthShut India", url: "https://mouthshut.com", relevance: "95%", rationale: "India's largest consumer review portal with thousands of verified trading app reviews." },
      { name: "Economic Times (ET Markets)", url: "https://economictimes.indiatimes.com", relevance: "92%", rationale: "Deep coverage of brokerage SLAs, trading outages, and SEBI compliance." },
      { name: "ValueResearch India", url: "https://valueresearchonline.com", rationale: "Expert and investor rating scorecards on Indian fintech platforms." },
      { name: "Google Play Store (India)", url: "https://play.google.com/store", relevance: "96%", rationale: "High-volume user feedback on mobile order execution & UI bugs." }
    ],
    sampleProducts: ["Zerodha", "Groww", "Razorpay", "Paytm", "PhonePe", "CRED"]
  },
  automotive: {
    categoryName: "Automotive & Electric Vehicles",
    icon: "Car",
    bestSources: [
      { name: "CarWale India", url: "https://carwale.com", relevance: "98%", rationale: "Real owner reviews, service center ratings, and real-world mileage reports." },
      { name: "ZigWheels", url: "https://zigwheels.com", relevance: "94%", rationale: "Detailed road test evaluations and long-term EV battery feedback." },
      { name: "MouthShut India", url: "https://mouthshut.com", relevance: "96%", rationale: "Extensive owner complaints and service center experience logs across Indian cities." },
      { name: "Team-BHP", url: "https://team-bhp.com", relevance: "99%", rationale: "India's most authoritative enthusiast automotive forum for deep technical reviews." },
      { name: "Gadgets360 (EV Tech)", url: "https://gadgets360.com", relevance: "90%", rationale: "In-depth smart infotainment and connected vehicle software reviews." }
    ],
    sampleProducts: ["Tata Nexon EV", "Mahindra XUV700", "Tesla Model 3", "Ola Electric", "Ather Energy"]
  },
  ecommerce_retail: {
    categoryName: "E-Commerce & Quick Commerce",
    icon: "ShoppingBag",
    bestSources: [
      { name: "MouthShut India", url: "https://mouthshut.com", relevance: "97%", rationale: "Verified delivery, refund, and product quality reviews from Indian buyers." },
      { name: "Flipkart Verified Reviews", url: "https://flipkart.com", relevance: "96%", rationale: "Direct buyer ratings on delivery speed, seller reliability, and packaging." },
      { name: "Amazon.in Verified Purchase", url: "https://amazon.in", relevance: "95%", rationale: "High volume customer feedback on logistics and product authenticity." },
      { name: "Inc42 / YourStory", url: "https://inc42.com", relevance: "90%", rationale: "Startup analysis on dark store coverage, delivery partner SLAs, and customer retention." },
      { name: "DesiDime Deals Community", url: "https://desidime.com", relevance: "91%", rationale: "Indian shopper community feedback on sale pricing, coupons, and customer service." }
    ],
    sampleProducts: ["Flipkart", "Blinkit", "Zepto", "Swiggy Instamart", "Meesho", "Myntra", "Nykaa"]
  },
  food_delivery: {
    categoryName: "Food Delivery & Dining Out",
    icon: "Utensils",
    bestSources: [
      { name: "MouthShut India", url: "https://mouthshut.com", relevance: "98%", rationale: "Dedicated restaurant delivery ratings, refund issues, and Gold subscription reviews." },
      { name: "Google Play Store (India)", url: "https://play.google.com/store", relevance: "95%", rationale: "Real-time user reports on order tracking, delivery executive behavior, and app crashes." },
      { name: "YourStory / Inc42", url: "https://yourstory.com", relevance: "89%", rationale: "Industry coverage on restaurant partner commission sentiment and service coverage." },
      { name: "Trustpilot India", url: "https://trustpilot.com/review/in", relevance: "91%", rationale: "Customer service SLA feedback and corporate dining account experiences." }
    ],
    sampleProducts: ["Zomato", "Swiggy", "Eatsure", "Dominos India"]
  },
  tech_saas: {
    categoryName: "SaaS, Cloud & Developer Tools",
    icon: "Cpu",
    bestSources: [
      { name: "ProductNation India", url: "https://productnation.in", relevance: "96%", rationale: "India SaaS ecosystem platform for product ratings and founder feedback." },
      { name: "G2 India & Global", url: "https://g2.com", relevance: "98%", rationale: "B2B software buyer reviews, feature scorecards, and implementation feedback." },
      { name: "YourStory Tech", url: "https://yourstory.com/tech", relevance: "92%", rationale: "Enterprise adoption coverage and developer ecosystem sentiment." },
      { name: "SoftwareAdvice India", url: "https://softwareadvice.com", relevance: "94%", rationale: "Detailed pricing tier evaluations and customer support SLA ratings." },
      { name: "HackerNews / TechCrunch", url: "https://news.ycombinator.com", relevance: "90%", rationale: "Developer experience, API quality, and keyboard navigation speed." }
    ],
    sampleProducts: ["Notion Workspace", "Linear App", "Zoho", "Freshworks", "Postman", "Razorpay Software"]
  },
  consumer_electronics: {
    categoryName: "Consumer Tech & Appliances",
    icon: "Smartphone",
    bestSources: [
      { name: "Gadgets360 (NDTV)", url: "https://gadgets360.com", relevance: "99%", rationale: "India's #1 tech review publication for smartphones, laptops, and smart devices." },
      { name: "91mobiles", url: "https://91mobiles.com", relevance: "96%", rationale: "Comprehensive spec comparison, battery benchmarks, and user review scores." },
      { name: "Digit India", url: "https://digit.in", relevance: "95%", rationale: "Deep hardware testing, display brightness labs, and performance scores." },
      { name: "Amazon.in / Flipkart Reviews", url: "https://amazon.in", relevance: "97%", rationale: "Mass customer ratings on thermal management, camera quality, and warranty service." },
      { name: "MouthShut India", url: "https://mouthshut.com", relevance: "94%", rationale: "After-sales service center ratings across Tier-1 and Tier-2 Indian cities." }
    ],
    sampleProducts: ["Apple Vision Pro", "Samsung Galaxy S-Series", "OnePlus", "Realme", "boAt Audio"]
  }
};

/**
 * Given any target product name, recommends the best sources to pull from
 */
export function getRecommendedSources(targetName) {
  const cleanName = (targetName || "").trim().toLowerCase();

  if (cleanName.includes("zerodha") || cleanName.includes("groww") || cleanName.includes("razorpay") || cleanName.includes("paytm") || cleanName.includes("cred") || cleanName.includes("phonepe") || cleanName.includes("upstox")) {
    return SOURCE_MATRIX.fintech;
  }
  if (cleanName.includes("tata") || cleanName.includes("mahindra") || cleanName.includes("car") || cleanName.includes("tesla") || cleanName.includes("ola electric") || cleanName.includes("ather") || cleanName.includes("hyundai")) {
    return SOURCE_MATRIX.automotive;
  }
  if (cleanName.includes("zomato") || cleanName.includes("swiggy") || cleanName.includes("food") || cleanName.includes("eatsure")) {
    return SOURCE_MATRIX.food_delivery;
  }
  if (cleanName.includes("flipkart") || cleanName.includes("blinkit") || cleanName.includes("zepto") || cleanName.includes("meesho") || cleanName.includes("myntra") || cleanName.includes("nykaa") || cleanName.includes("amazon")) {
    return SOURCE_MATRIX.ecommerce_retail;
  }
  if (cleanName.includes("notion") || cleanName.includes("linear") || cleanName.includes("zoho") || cleanName.includes("freshworks") || cleanName.includes("slack") || cleanName.includes("figma")) {
    return SOURCE_MATRIX.tech_saas;
  }
  if (cleanName.includes("apple") || cleanName.includes("samsung") || cleanName.includes("oneplus") || cleanName.includes("phone") || cleanName.includes("vision") || cleanName.includes("boat") || cleanName.includes("gadget")) {
    return SOURCE_MATRIX.consumer_electronics;
  }

  // Default smart fallback for general Indian targets
  return {
    categoryName: "General Market Product",
    icon: "Globe",
    bestSources: [
      { name: "MouthShut India", url: "https://mouthshut.com", relevance: "97%", rationale: "India's premier consumer opinion platform across products & services." },
      { name: "Economic Times (ET Tech)", url: "https://economictimes.indiatimes.com", relevance: "94%", rationale: "Reputable corporate media coverage on customer sentiment & market reception." },
      { name: "YourStory / Inc42", url: "https://yourstory.com", relevance: "91%", rationale: "Leading Indian business & tech ecosystem coverage." },
      { name: "Google Play Store (India)", url: "https://play.google.com/store", relevance: "95%", rationale: "High-volume user ratings and mobile app operational feedback." },
      { name: "Amazon.in Verified Purchase", url: "https://amazon.in", relevance: "92%", rationale: "Verified buyer product feedback." }
    ],
    sampleProducts: [cleanName]
  };
}
