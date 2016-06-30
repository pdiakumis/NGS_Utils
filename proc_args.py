from collections import OrderedDict
from os.path import splitext, basename

from Utils.bam_bed_utils import verify_bam
from Utils.file_utils import verify_file, adjust_path, splitext_plus
from Utils.logger import info, critical, err


def read_samples(args):
    bam_by_sample = find_bams(args)
    if bam_by_sample:
        info('Found ' + str(len(bam_by_sample)) + ' BAM file' + ('s' if len(bam_by_sample) > 1 else ''))

    input_not_bam = [verify_file(fpath) for fpath in args if adjust_path(fpath) not in bam_by_sample]
    input_not_bam = [fpath for fpath in input_not_bam if fpath]
    fastqs_by_sample = dict()
    if not input_not_bam and not bam_by_sample:
        critical('No correct input files')
    if input_not_bam:
        info(str(len(input_not_bam)) + ' correct input not-bam files')
        fastqs_by_sample = find_fastq_pairs(input_not_bam)
        if fastqs_by_sample:
            info('Found FastQ pairs: ' + str(len(fastqs_by_sample)))
        intersection = set(fastqs_by_sample.keys()) & set(bam_by_sample.keys())
        if intersection:
            critical('The following samples both had input BAMs and FastQ: ' + ', '.join(list(intersection)))

    return fastqs_by_sample, bam_by_sample


def find_bams(args):
    bam_by_sample = OrderedDict()
    bad_bam_fpaths = []

    good_args = []
    for arg in args:
        # /ngs/oncology/Analysis/bioscience/Bio_0038_KudosCellLinesExomes/Bio_0038_150521_D00443_0159_AHK2KTADXX/bcbio,Kudos159 /ngs/oncology/Analysis/bioscience/Bio_0038_KudosCellLinesExomes/Bio_0038_150521_D00443_0160_BHKWMNADXX/bcbio,Kudos160
        fpath = arg.split(',')[0]
        fname, ext = splitext(fpath)
        if ext == '.bam':
            bam_fpath = verify_bam(fpath)
            if not bam_fpath:
                bad_bam_fpaths.append(fpath)
            else:
                if len(arg.split(',')) > 1:
                    sname = arg.split(',')[1]
                else:
                    sname = basename(splitext(bam_fpath)[0])
                bam_by_sample[sname] = bam_fpath
                good_args.append(arg)
    if bad_bam_fpaths:
        critical('BAM files cannot be found, empty or not BAMs: ' + ', '.join(bad_bam_fpaths))
    for arg in good_args:
        args.remove(arg)

    return bam_by_sample


def find_fastq_pairs(fpaths):
    info('Finding fastq pairs.')
    fastqs_by_sample_name = dict()
    for fpath in fpaths:
        fn, ext = splitext_plus(basename(fpath))
        if ext in ['.fq', '.fq.gz', '.fastq', '.fastq.gz']:
            sname, l_fpath, r_fpath = None, None, None
            if fn.endswith('_1'):
                sname = fn[:-2]
                l_fpath = fpath
            if fn.endswith('_R1'):
                sname = fn[:-3]
                l_fpath = fpath
            if fn.endswith('_2'):
                sname = fn[:-2]
                r_fpath = fpath
            if fn.endswith('_R2'):
                sname = fn[:-3]
                r_fpath = fpath
            if not sname:
                sname = fn
                info('Cannot detect file for ' + sname)

            l, r = fastqs_by_sample_name.get(sname, (None, None))
            if l and l_fpath:
                critical('Duplicated left FastQ files for ' + sname + ': ' + l + ' and ' + l_fpath)
            if r and r_fpath:
                critical('Duplicated right FastQ files for ' + sname + ': ' + r + ' and ' + r_fpath)
            fastqs_by_sample_name[sname] = l or l_fpath, r or r_fpath

    fixed_fastqs_by_sample_name = dict()
    for sname, (l, r) in fastqs_by_sample_name.items():
        if not l:
            err('ERROR: for sample ' + sname + ', left reads not found')
        if not r:
            err('ERROR: for sample ' + sname + ', left reads not found')
        fixed_fastqs_by_sample_name[sname] = l, r

    return fixed_fastqs_by_sample_name
