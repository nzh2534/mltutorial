import os
import io
import fitz #PyMuPDF==1.22.3
import boto3 #boto3==1.26.147
import requests #requests==2.31.0
import numpy as np #numpy==1.24.3
from PIL import Image
from django.conf import settings
from botocore.exceptions import ClientError #botocore==1.29.147

#Sets up and AWS session using boto3
session = boto3.Session(
aws_access_key_id= os.environ['AWS_ACCESS_KEY_ID'],
aws_secret_access_key= os.environ['AWS_SECRET_ACCESS_KEY'],
)
s3_client = session.client('s3')
s3_resource = session.resource('s3')

#A function to save your files to a bucket
def upload_src(src, filename, bucketName):
    success = False
    try:
        bucket = s3_resource.Bucket(bucketName)
    except ClientError as e:
        print(e)
        bucket = None

    try:
        s3_obj = bucket.Object(filename)
    except (ClientError, AttributeError) as e:
        print(e)
        s3_obj = None

    try:
        s3_obj.upload_fileobj(src, ExtraArgs={'ACL':'public-read'})
    except (ClientError, AttributeError) as e:
        print(e)
        pass

    return success

def mltask(file_path):
    #Importing Detectron2 here will save your Heroku web process memory
    # and only incur it on the Celery worker
    from detectron2.config import get_cfg
    from detectron2.engine import DefaultPredictor
    from detectron2 import model_zoo
    cfg = get_cfg()

    #Use the same config_file_path used in Part 1 for training
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.DEVICE = "cpu"

    #The threshold used to filter out low-scored bounding boxes
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.3

    #The path to model_final.pth
    cfg.MODEL.WEIGHTS = os.environ['MODEL_PATH']

    # Number of foreground classes, 
    # We had used title/header for annotation in Part 1
    # If you trained the model to detect more than one object in Part 1
    # then increase NUM_CLASSES to the number of objects
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1

    #The loaded model with configurations
    predictor = DefaultPredictor(cfg)

    #Retrieve the saved PDF from S3
    res = requests.get(settings.MEDIA_URL + file_path)
    doc = fitz.open(stream=res.content, filetype="pdf")

    #Settings for PyMuPDF package fitz
    zoom_x = 1.5
    zoom_y = 1.5
    mat = fitz.Matrix(zoom_x, zoom_y)
    
    index = 0
    while index < doc.page_count:
        print(f'Running for page {str(index + 1)}')

        #Load the base image
        pix = doc.load_page(index).get_pixmap(matrix=mat)
        base_img = Image.frombytes(
            "RGBA" if pix.alpha else "RGB", 
            [pix.width, pix.height], 
            pix.samples
            )
        #Convert the base image to a numpy array
        img = np.array(base_img)

        #Detectron2 will now detect objects in the array
        inferences = predictor(img)

        #Here is one option to filter your inferences based on score
        #Score here means how confident the model is that the object
        #detected 
        inferences_filtered = inferences['instances'][inferences['instances'].scores > 0.9]

        #Iterate over inferences and save to S3
        for prediction_number, box in enumerate(inferences_filtered.pred_boxes):
            in_mem_file = io.BytesIO()
            base_img.crop(
                    (float(box[0]),float(box[1]),float(box[2]),float(box[3]))
                ).save(
                    in_mem_file, format="PNG"
                )
            in_mem_file.seek(0)
            upload_src(in_mem_file, f"media/page{str(index + 1)}_{str(prediction_number)}.jpg", os.environ['AWS_STORAGE_BUCKET_NAME'])
        
        index += 1

