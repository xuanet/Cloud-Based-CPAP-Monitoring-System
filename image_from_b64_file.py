from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt


def display_image_from_b64_file(file_path):
    with open(file_path, "rb") as f:
        image_bytes = f.read()

    image = Image.open(BytesIO(image_bytes))

    plt.imshow(image)
    plt.axis('off')
    plt.show()


display_image_from_b64_file("1, 2024-04-23 23:25:27")
