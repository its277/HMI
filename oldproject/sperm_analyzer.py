import numpy as np
from skimage.morphology import skeletonize
from scipy.spatial.distance import euclidean

def is_tail_bent(mask, threshold=1.15):
    """
    Analyzes a sperm's segmentation mask to check for a bent tail.

    Args:
        mask (np.array): A 2D binary numpy array of the sperm's mask.
        threshold (float): Ratio of skeleton path length to endpoint distance
                           to classify a tail as bent.

    Returns:
        bool: True if the tail is considered bent, False otherwise.
    """
    if mask is None or np.sum(mask) == 0:
        return False

    # The mask from YOLO might not be binary, so convert it
    binary_mask = (mask > 0).astype(np.uint8)
    
    # Skeletonize the mask to get a 1-pixel wide representation
    skeleton = skeletonize(binary_mask)

    # Find the coordinates of the skeleton pixels
    points = np.argwhere(skeleton)
    if len(points) < 5:  # Not enough points to be a sperm
        return False

    # Find endpoints by finding points with only one neighbor
    endpoints = []
    for y, x in points:
        # Check 8-connectivity neighborhood
        neighbors = np.sum(skeleton[y-1:y+2, x-1:x+2]) - 1
        if neighbors == 1:
            endpoints.append((y, x))
    
    # We expect two endpoints for a simple line (sperm)
    if len(endpoints) != 2:
        # Could be a noisy segmentation or a branched skeleton
        return False
        
    start_point, end_point = endpoints[0], endpoints[1]
    
    # Calculate the direct distance between endpoints
    direct_distance = euclidean(start_point, end_point)

    # The number of pixels in the skeleton is a good proxy for its path length
    path_length = len(points)

    if direct_distance == 0: # Avoid division by zero
        return False

    # Calculate the ratio
    ratio = path_length / direct_distance
    
    # If the path is much longer than the straight line, it's bent
    return ratio > threshold
