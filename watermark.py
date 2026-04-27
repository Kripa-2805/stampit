import os

def stamp_video(file_obj):
    """
    Cloud-Optimized Demo Version:
    Bypasses heavy OpenCV processing to avoid 512MB RAM crash on Render Free Tier.
    Simulates the invisible watermarking process instantly.
    """
    print("Simulating invisible watermarking for cloud deployment...")
    
    # 1. Ensure the output folder exists
    output_dir = 'static/protected/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. Create the new filename
    original_name = file_obj.filename
    stamped_filename = f"stamped_{original_name}"
    output_path = os.path.join(output_dir, stamped_filename)

    # 3. Save the file instantly (bypassing OpenCV RAM limits)
    file_obj.save(output_path)
    
    return output_path
